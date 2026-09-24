import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.compatibility.models import GoalResult, MenuItemInput, SafetyResult, UserProfileInput
from app.compatibility.safety import check_safety
from app.compatibility.goals import check_nutrition_goals
from app.compatibility.scoring import combine_scores
from app.llm.questions import generate_questions_with_llm
from app.llm.groq_client import GroqLookupError, generate_chat_completion
from app.services.compatibility_service import run_compatibility_check


def ingredient(found=True, labels=(), **nutrients):
    return SimpleNamespace(found=found, health_labels=list(labels), nutrients=nutrients)


class CompatibilityTests(unittest.TestCase):
    def test_conflict_overrides_favorable_goals(self):
        with patch('app.compatibility.safety.get_or_fetch', return_value=ingredient()):
            safety = check_safety(None, MenuItemInput('Peanut sauce', ['peanut']),
                                  UserProfileInput(allergens=['Peanut']))
        report = combine_scores(safety, GoalResult(goal_scores={'High Protein': 100}))
        self.assertEqual(report.compatibility_score, 0)
        self.assertEqual(report.detected_allergens, ['Peanut'])
        self.assertEqual(report.suggested_modifications, ['Remove peanut'])

    def test_unknown_ingredient_never_gets_perfect_score(self):
        with patch('app.compatibility.safety.get_or_fetch', return_value=ingredient(found=False)):
            safety = check_safety(None, MenuItemInput('Dish', ['sauce']), UserProfileInput())
        report = combine_scores(safety, GoalResult())
        self.assertIsNone(report.compatibility_score)
        self.assertIsNone(report.safety_score)
        self.assertEqual(report.confidence, 'Low')
        self.assertTrue(report.questions_to_ask)

    def test_empty_ingredients_are_unassessed(self):
        safety = check_safety(None, MenuItemInput('Dish', []), UserProfileInput())
        self.assertIsNone(combine_scores(safety, GoalResult()).compatibility_score)
        self.assertEqual(safety.confidence, 'Low')

    def test_unimplemented_dietary_style_is_disclosed(self):
        with patch('app.compatibility.safety.get_or_fetch', return_value=ingredient()):
            safety = check_safety(None, MenuItemInput('Dish', ['rice']),
                                  UserProfileInput(dietary_styles=['Vegan']))
        self.assertIsNone(safety.safety_score)
        self.assertIn('Vegan', safety.warnings[0])

    def test_missing_nutrients_do_not_become_perfect_score(self):
        with patch('app.compatibility.goals.get_or_fetch', return_value=ingredient()):
            goals = check_nutrition_goals(None, MenuItemInput('Dish', ['rice']),
                                         UserProfileInput(nutrition_goals=['High Protein']))
        self.assertEqual(goals.unassessed_goals, ['High Protein'])
        self.assertIsNone(combine_scores(SafetyResult(100, 'High'), goals).compatibility_score)

    def test_partial_nutrients_preserve_partial_score_but_no_overall(self):
        with patch('app.compatibility.goals.get_or_fetch', side_effect=[ingredient(PROCNT=20), ingredient()]):
            goals = check_nutrition_goals(None, MenuItemInput('Dish', ['chicken', 'sauce']),
                                         UserProfileInput(nutrition_goals=['High Protein']))
        result = combine_scores(SafetyResult(100, 'High'), goals)
        self.assertEqual(result.goal_score, 100)
        self.assertIsNone(result.compatibility_score)

    def test_maintenance_is_unassessed(self):
        with patch('app.compatibility.goals.get_or_fetch', return_value=ingredient()):
            goals = check_nutrition_goals(None, MenuItemInput('Dish', ['rice']),
                                         UserProfileInput(nutrition_goals=['Weight Maintenance']))
        self.assertEqual(goals.unassessed_goals, ['Weight Maintenance'])
        self.assertEqual(goals.goal_scores, {})

    def test_complete_data_averages_goals(self):
        result = combine_scores(SafetyResult(100, 'High'), GoalResult(goal_scores={'A': 50, 'B': 100}))
        self.assertEqual(result.compatibility_score, 75)

    def test_no_goals_with_known_ingredients(self):
        self.assertEqual(combine_scores(SafetyResult(100, 'High'), GoalResult()).compatibility_score, 100)

    def test_invalid_ai_questions_use_fallback(self):
        for response in ['not json', '{}', '[]', '[""]', '[1]']:
            with self.subTest(response=response), patch('app.llm.questions.generate_chat_completion', return_value=response):
                self.assertIsNone(generate_questions_with_llm('Dish', ['sauce'], ['Peanut']))

    def test_ai_failure_preserves_deterministic_questions(self):
        user = SimpleNamespace(allergens=[], medical_restrictions=[], dietary_styles=[], nutrition_goals=[])
        with patch('app.compatibility.safety.get_or_fetch', return_value=ingredient(found=False)), \
             patch('app.compatibility.goals.get_or_fetch', return_value=ingredient(found=False)), \
             patch('app.llm.questions.generate_chat_completion', side_effect=GroqLookupError('timeout')):
            report = run_compatibility_check(None, user, MenuItemInput('Dish', ['sauce']))
        self.assertEqual(report.questions_to_ask, ['What are the ingredients in the sauce?'])
        self.assertIsNone(report.compatibility_score)

    def test_bad_provider_json_is_wrapped(self):
        with patch('app.llm.groq_client.httpx.post') as post:
            post.return_value.json.side_effect = ValueError('invalid JSON')
            with self.assertRaises(GroqLookupError):
                generate_chat_completion('system', 'user')


if __name__ == '__main__':
    unittest.main()
