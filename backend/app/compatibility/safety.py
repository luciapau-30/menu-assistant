from sqlalchemy.orm import Session

from app.compatibility.label_mapping import (
    ALLERGEN_TO_EDAMAM_LABEL,
    MEDICAL_RESTRICTION_TO_EDAMAM_LABEL,
)
from app.compatibility.models import MenuItemInput, SafetyResult, UserProfileInput
from app.services.ingredient_cache_service import get_or_fetch


def check_safety(
    db: Session, menu_item: MenuItemInput, profile: UserProfileInput
) -> SafetyResult:
    user_allergens = {a for a in profile.allergens if a != "None"}
    user_restrictions = {r for r in profile.medical_restrictions if r != "None"}

    detected_allergens = set()
    detected_restrictions = set()
    unknown_ingredients = []
    offending_ingredients = set()

    for raw_ingredient in menu_item.ingredients:
        cache_entry = get_or_fetch(db, raw_ingredient)

        if not cache_entry.found:
            unknown_ingredients.append(raw_ingredient)
            continue

        health_labels = set(cache_entry.health_labels)
        ingredient_is_offending = False

        for allergen in user_allergens:
            edamam_label = ALLERGEN_TO_EDAMAM_LABEL.get(allergen)
            if edamam_label and edamam_label not in health_labels:
                detected_allergens.add(allergen)
                ingredient_is_offending = True

        for restriction in user_restrictions:
            edamam_label = MEDICAL_RESTRICTION_TO_EDAMAM_LABEL.get(restriction)
            if edamam_label and edamam_label not in health_labels:
                detected_restrictions.add(restriction)
                ingredient_is_offending = True

        if ingredient_is_offending:
            offending_ingredients.add(raw_ingredient)

    is_unsafe = bool(detected_allergens or detected_restrictions)
    unsupported = (
        user_allergens - ALLERGEN_TO_EDAMAM_LABEL.keys()
        | user_restrictions - MEDICAL_RESTRICTION_TO_EDAMAM_LABEL.keys()
        | (set(profile.dietary_styles) - {"None"})
    )
    incomplete = bool(unknown_ingredients or not menu_item.ingredients or unsupported)
    safety_score = 0 if is_unsafe else (None if incomplete else 100)

    total_ingredients = len(menu_item.ingredients)
    unknown_ratio = (
        len(unknown_ingredients) / total_ingredients if total_ingredients else 0
    )

    if not menu_item.ingredients or unsupported:
        confidence = "Low"
    elif unknown_ratio == 0:
        confidence = "High"
    elif unknown_ratio <= 0.34:
        confidence = "Medium"
    else:
        confidence = "Low"

    warnings = []
    if not menu_item.ingredients:
        warnings.append("No ingredients supplied; compatibility cannot be assessed.")
    if unsupported:
        warnings.append("Profile selections not yet assessed: " + ", ".join(sorted(unsupported)))
    if unknown_ingredients:
        warnings.append(
            "Ingredient(s) not recognized, could not be checked: "
            + ", ".join(unknown_ingredients)
        )

    suggested_modifications = [
        f"Remove {ingredient}" for ingredient in sorted(offending_ingredients)
    ]

    user_concerns = sorted(user_allergens | user_restrictions)
    questions_to_ask = []
    for ingredient in unknown_ingredients:
        if user_concerns:
            questions_to_ask.append(
                f"Does the {ingredient} contain {', '.join(user_concerns)}?"
            )
        else:
            questions_to_ask.append(f"What are the ingredients in the {ingredient}?")

    return SafetyResult(
        safety_score=safety_score,
        confidence=confidence,
        detected_allergens=sorted(detected_allergens),
        detected_restrictions=sorted(detected_restrictions),
        unknown_ingredients=unknown_ingredients,
        warnings=warnings,
        suggested_modifications=suggested_modifications,
        questions_to_ask=questions_to_ask,
    )
