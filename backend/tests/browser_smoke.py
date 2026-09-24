"""Optional browser smoke: python -m tests.browser_smoke (requires Playwright + Chrome)."""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from tests.test_analysis import AnalysisTests, EXTRACTED
from app.core.deps import get_current_user
from app.main import app
from app.models.allergen import Allergen
from app.schemas.extraction import Extraction


def main():
    from playwright.sync_api import sync_playwright

    fixture = AnalysisTests()
    fixture.setUp()
    try:
        fixture.db.add(Allergen(name='None'))
        fixture.db.commit()
        app.dependency_overrides.pop(get_current_user)
        ingredient = SimpleNamespace(found=True, health_labels=[], nutrients={})
        with patch('app.llm.vision.extract_image', return_value=Extraction.model_validate(EXTRACTED)), \
             patch('app.compatibility.safety.get_or_fetch', return_value=ingredient), \
             patch('app.compatibility.goals.get_or_fetch', return_value=ingredient), sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            errors = []
            page.set_default_timeout(10000)
            page.on('pageerror', lambda error: errors.append(str(error)))

            def respond(route):
                request = route.request
                headers = {key: value for key, value in request.headers.items()
                           if key in ('content-type', 'authorization')}
                path = request.url.replace('http://pom.test', '')
                if path == '/api/v1/analysis/upload':
                    # Chrome interception can omit file bytes from multipart post data.
                    image = Path(__file__).parents[1] / 'evals/images/explicit_menu.png'
                    response = fixture.client.post(path, headers={
                        'authorization': headers.get('authorization', '')},
                        data={'type': 'MENU'}, files={'image': ('menu.png', image.read_bytes(), 'image/png')})
                else:
                    response = fixture.client.request(request.method, path,
                                                      headers=headers, content=request.post_data_buffer)
                if response.status_code >= 400:
                    print(path, response.status_code, response.text, flush=True)
                route.fulfill(status=response.status_code, body=response.content,
                              headers={'content-type': response.headers.get('content-type', 'text/plain')})

            page.route('**/*', respond)
            page.goto('http://pom.test/app/')
            page.get_by_label('Name', exact=True).fill('Browser User')
            page.get_by_label('Email', exact=True).fill('browser@example.com')
            page.get_by_label('Password', exact=True).fill('test-password')
            page.get_by_role('button', name='Create account').click()
            page.locator('select[name=allergens]').select_option('None')
            page.get_by_role('button', name='Save profile').click()
            page.get_by_text('Profile saved. You can upload a menu now.').wait_for()
            page.get_by_label('Image', exact=True).set_input_files(str(Path(__file__).parents[1] / 'evals/images/explicit_menu.png'))
            page.get_by_role('button', name='Upload and read image').click()
            page.get_by_label('Item name', exact=True).wait_for()
            page.get_by_label('Item name', exact=True).fill('Reviewed Rice Bowl')
            page.get_by_role('button', name='Generate reports').click()
            page.get_by_role('heading', name='Reviewed Rice Bowl').wait_for()
            assert page.get_by_text('100 / 100', exact=True).is_visible()
            page.screenshot(path='/tmp/pom-browser-desktop.png', full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path='/tmp/pom-browser-mobile.png', full_page=True)
            assert not errors, errors
            browser.close()
        print('Browser smoke passed: registration, profile, upload, review, reports, mobile width; no JS errors.')
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
