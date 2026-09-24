"""
Maps our own allergen / medical-restriction category names (as seeded in
the allergens / medical_restrictions tables) to the corresponding Edamam
Food Database "health label" that indicates a food is free of it.

If a food's health_labels list does NOT contain the mapped label, we treat
that category as not confirmed safe for that food.
"""

ALLERGEN_TO_EDAMAM_LABEL: dict[str, str] = {
    "Peanut": "PEANUT_FREE",
    "Tree Nut": "TREE_NUT_FREE",
    "Dairy": "DAIRY_FREE",
    "Egg": "EGG_FREE",
    "Soy": "SOY_FREE",
    "Wheat": "WHEAT_FREE",
    "Fish": "FISH_FREE",
    "Shellfish": "SHELLFISH_FREE",
    "Sesame": "SESAME_FREE",
}

MEDICAL_RESTRICTION_TO_EDAMAM_LABEL: dict[str, str] = {
    "Celiac Disease": "GLUTEN_FREE",
    "Gluten Intolerance": "GLUTEN_FREE",
    "Lactose Intolerance": "DAIRY_FREE",
    "Low FODMAP": "FODMAP_FREE",
}
