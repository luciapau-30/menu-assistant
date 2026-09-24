from sqlalchemy.orm import Session

from app.compatibility.models import GoalResult, MenuItemInput, UserProfileInput
from app.services.ingredient_cache_service import get_or_fetch

# All thresholds are per-100g nutrient density (see docs/03_ARCHITECTURE.md
# "Compatibility Engine Methodology" for the reasoning behind these values).
PROTEIN_RICH_THRESHOLD = 15  # g protein / 100g
LOW_CARB_THRESHOLD = 20  # g carbs / 100g
WEIGHT_LOSS_CALORIE_THRESHOLD = 200  # kcal / 100g
WEIGHT_LOSS_PROTEIN_THRESHOLD = 10  # g protein / 100g
WEIGHT_LOSS_FIBER_THRESHOLD = 3  # g fiber / 100g


def _is_favorable_for_goal(goal: str, nutrients: dict) -> bool | None:
    """
    Returns whether a single ingredient's composition favors the given
    goal, or None if we don't have enough data to judge it for this goal.
    """
    protein = nutrients.get("PROCNT")
    carbs = nutrients.get("CHOCDF")
    calories = nutrients.get("ENERC_KCAL")
    fiber = nutrients.get("FIBTG")

    if goal in ("High Protein", "Muscle Gain"):
        if protein is None:
            return None
        return protein >= PROTEIN_RICH_THRESHOLD

    if goal == "Low Carb":
        if carbs is None:
            return None
        return carbs < LOW_CARB_THRESHOLD

    if goal == "Weight Loss":
        if calories is None or (protein is None and fiber is None):
            return None
        low_calorie_density = calories < WEIGHT_LOSS_CALORIE_THRESHOLD
        satiating = (protein is not None and protein >= WEIGHT_LOSS_PROTEIN_THRESHOLD) or (
            fiber is not None and fiber >= WEIGHT_LOSS_FIBER_THRESHOLD
        )
        return low_calorie_density and satiating

    return None


def check_nutrition_goals(
    db: Session, menu_item: MenuItemInput, profile: UserProfileInput
) -> GoalResult:
    user_goals = {g for g in profile.nutrition_goals if g != "None"}

    ingredient_nutrients = []
    unknown_ingredients = []

    for raw_ingredient in menu_item.ingredients:
        cache_entry = get_or_fetch(db, raw_ingredient)
        if not cache_entry.found:
            unknown_ingredients.append(raw_ingredient)
            continue
        ingredient_nutrients.append(cache_entry.nutrients)

    goal_scores: dict[str, int] = {}
    unassessed_goals: list[str] = []

    for goal in user_goals:
        if goal == "Weight Maintenance":
            # Ingredient composition alone can't assess maintenance -- it
            # depends on total daily calories, not any single dish.
            unassessed_goals.append(goal)
            continue

        favorable_count = 0
        known_count = 0

        for nutrients in ingredient_nutrients:
            favorable = _is_favorable_for_goal(goal, nutrients)
            if favorable is None:
                continue
            known_count += 1
            if favorable:
                favorable_count += 1

        if known_count < len(menu_item.ingredients) or not known_count:
            unassessed_goals.append(goal)
        if known_count == 0:
            continue

        goal_scores[goal] = round(100 * favorable_count / known_count)

    return GoalResult(
        goal_scores=goal_scores,
        unassessed_goals=sorted(unassessed_goals),
        unknown_ingredients=unknown_ingredients,
    )
