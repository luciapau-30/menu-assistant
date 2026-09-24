import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.database.connection import Base, get_db
from app.main import app
from app.models.user import User
from app.models.analysis import Analysis, AnalysisStatus
from app.schemas.extraction import Extraction
from app.llm.vision import ExtractionError, extract_image

PNG = b'\x89PNG\r\n\x1a\nexample'
EXTRACTED = {'items': [{'name': 'Rice bowl', 'ingredients': ['rice'], 'source_text': 'Rice bowl: rice'}], 'warnings': []}


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        tables = [t for t in Base.metadata.sorted_tables if t.name != 'ingredient_cache']
        Base.metadata.create_all(self.engine, tables=tables)
        self.db = sessionmaker(bind=self.engine)()
        self.addCleanup(self.db.close)
        self.user = User(name='Test', email='test@example.com', password_hash='unused')
        self.db.add(self.user)
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.start_patch('app.core.storage.UPLOAD_DIR', self.temp.name)
        self.start_patch('httpx.post', side_effect=AssertionError('Unexpected external API call'))
        self.start_patch('httpx.get', side_effect=AssertionError('Unexpected external API call'))

    def start_patch(self, target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def upload(self):
        response = self.client.post('/api/v1/analysis/upload', data={'type': 'MENU'},
                                    files={'image': ('menu.png', PNG, 'image/png')})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['analysis_id']

    def test_account_profile_and_demo_page(self):
        from app.models.allergen import Allergen
        self.db.add(Allergen(name='Peanut'))
        self.db.commit()
        app.dependency_overrides.pop(get_current_user)
        self.assertIn(self.client.get('/api/v1/profile').status_code, (401, 403))
        response = self.client.post('/api/v1/auth/register', json={
            'name': 'New user', 'email': 'new@example.com', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post('/api/v1/auth/login', json={
            'email': 'new@example.com', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200, response.text)
        self.client.headers['Authorization'] = 'Bearer ' + response.json()['access_token']
        options = self.client.get('/api/v1/profile/options')
        self.assertEqual(options.json()['allergens'], ['Peanut'])
        response = self.client.put('/api/v1/profile', json={'allergens': ['Peanut']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get('/api/v1/profile').json()['allergens'], ['Peanut'])
        self.assertEqual(self.client.get('/app/').status_code, 200)
        self.assertIn('Review your ingredients', self.client.get('/app/').text)
        self.assertEqual(self.client.get('/app/app.js').status_code, 200)

    def test_upload_review_report_round_trip(self):
        analysis_id = self.upload()
        with patch('app.llm.vision.extract_image', return_value=Extraction.model_validate(EXTRACTED)):
            response = self.client.post(f'/api/v1/analysis/{analysis_id}/extract')
        data = response.json()
        self.assertEqual(data['status'], 'UPLOADED')
        self.assertEqual(data['extraction'], EXTRACTED)
        self.assertIsNone(data['reports'])
        cached = SimpleNamespace(found=True, health_labels=[], nutrients={'PROCNT': 2})
        with patch('app.compatibility.safety.get_or_fetch', return_value=cached), \
             patch('app.compatibility.goals.get_or_fetch', return_value=cached):
            response = self.client.post(f'/api/v1/analysis/{analysis_id}/report',
                                        json={'items': [{'name': 'Reviewed bowl', 'ingredients': ['rice']}]})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['status'], 'COMPLETED')
        self.assertEqual(data['reports'][0]['menu_item_name'], 'Reviewed bowl')
        self.assertEqual(data['reports'][0]['ingredients'], ['rice'])
        self.assertEqual(data['reports'][0]['compatibility_score'], 100)
        self.assertEqual(data['profile_snapshot']['name'], 'Test')
        self.db.expire_all()
        self.assertEqual(self.client.get(f'/api/v1/analysis/{analysis_id}').json(), data)
        self.assertEqual(self.client.post(f'/api/v1/analysis/{analysis_id}/extract').status_code, 409)

    def test_other_users_cannot_read_or_process_upload(self):
        analysis_id = self.upload()
        other = User(name='Other', email='other@example.com', password_hash='unused')
        self.db.add(other)
        self.db.commit()
        app.dependency_overrides[get_current_user] = lambda: other
        self.assertEqual(self.client.get(f'/api/v1/analysis/{analysis_id}').status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/analysis/{analysis_id}/extract').status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/analysis/{analysis_id}/report',
                         json={'items': [{'name': 'Dish', 'ingredients': ['rice']}]}).status_code, 404)

    def test_extraction_failure_can_retry(self):
        analysis_id = self.upload()
        with patch('app.llm.vision.extract_image', side_effect=ExtractionError('Retry extraction')):
            response = self.client.post(f'/api/v1/analysis/{analysis_id}/extract')
        self.assertEqual(response.json()['status'], 'FAILED')
        self.assertEqual(response.json()['error_message'], 'Retry extraction')
        with patch('app.llm.vision.extract_image', return_value=Extraction.model_validate(EXTRACTED)):
            response = self.client.post(f'/api/v1/analysis/{analysis_id}/extract')
        self.assertEqual(response.json()['status'], 'UPLOADED')
        self.assertIsNone(response.json()['error_message'])

    def test_report_failure_does_not_save_partial_reports(self):
        analysis_id = self.upload()
        with patch('app.services.compatibility_service.run_compatibility_check', side_effect=RuntimeError('private details')):
            response = self.client.post(f'/api/v1/analysis/{analysis_id}/report',
                                       json={'items': [{'name': 'Dish', 'ingredients': ['rice']}]})
        self.assertEqual(response.json()['status'], 'FAILED')
        self.assertIsNone(response.json()['reports'])
        self.assertNotIn('private details', response.text)

    def test_processing_cannot_be_claimed_twice(self):
        analysis_id = self.upload()
        analysis = self.db.get(Analysis, analysis_id)
        analysis.status = AnalysisStatus.PROCESSING
        self.db.commit()
        self.assertEqual(self.client.post(f'/api/v1/analysis/{analysis_id}/extract').status_code, 409)

    def test_invalid_upload_and_empty_review(self):
        response = self.client.post('/api/v1/analysis/upload', data={'type': 'MENU'},
                                    files={'image': ('fake.png', b'not an image', 'image/png')})
        self.assertEqual(response.status_code, 415)
        response = self.client.post('/api/v1/analysis/upload', data={'type': 'MENU'},
                                    files={'image': ('large.png', PNG + b'x' * (4 * 1024 * 1024), 'image/png')})
        self.assertEqual(response.status_code, 413)
        analysis_id = self.upload()
        response = self.client.post(f'/api/v1/analysis/{analysis_id}/report',
                                    json={'items': [{'name': 'Dish', 'ingredients': []}]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get(f'/api/v1/analysis/{analysis_id}').json()['status'], 'UPLOADED')

    def test_vision_validates_output_and_sends_image(self):
        image = Path(self.temp.name) / 'menu.png'
        image.write_bytes(PNG)
        with patch('app.llm.vision.httpx.post') as post:
            post.return_value.json.return_value = {'choices': [{'finish_reason': 'stop', 'message': {'content': Extraction.model_validate(EXTRACTED).model_dump_json()}}]}
            result = extract_image(str(image), 'MENU')
            self.assertEqual(result.items[0].ingredients, ['rice'])
            payload = post.call_args.kwargs['json']
            self.assertTrue(payload['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            post.return_value.json.return_value = {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
            with self.assertRaises(ExtractionError):
                extract_image(str(image), 'MENU')
            post.return_value.json.return_value = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"items": []}'}}]}
            with self.assertRaises(ExtractionError):
                extract_image(str(image), 'MENU')


if __name__ == '__main__':
    unittest.main()
