import unittest
from evals.run import measure


class EvaluationTests(unittest.TestCase):
    def test_invented_ingredients_on_names_only_menu_are_counted(self):
        result = measure({'items': [{'name': 'Burger', 'ingredients': []}]},
                         {'items': [{'name': 'Burger', 'ingredients': ['beef']}]})
        self.assertFalse(result['exact_match'])
        self.assertEqual(result['invented_ingredients'], [['burger', 'beef']])
        self.assertEqual(result['ingredient_precision'], 0)

    def test_missing_item_is_not_a_perfect_match(self):
        result = measure({'items': [{'name': 'Soup', 'ingredients': []}]}, {'items': []})
        self.assertFalse(result['exact_match'])
        self.assertEqual(result['missing_items'], ['soup'])
