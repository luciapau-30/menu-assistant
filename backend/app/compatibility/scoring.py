from app.compatibility.models import CompatibilityResult, GoalResult, SafetyResult


def combine_scores(safety: SafetyResult, goals: GoalResult) -> CompatibilityResult:
    """
    Combines safety detection and goal matching into one compatibility
    report. A detected conflict scores 0. Incomplete assessments have no
    overall score; partial goal scores remain available for transparency.
    With complete data, use goal fit, or 100 when no goals were selected.
    """
    if safety.safety_score == 0:
        compatibility_score = 0
        goal_score = None
    elif (safety.safety_score is None or safety.unknown_ingredients
          or goals.unknown_ingredients or goals.unassessed_goals):
        compatibility_score = None
        goal_score = (
            round(sum(goals.goal_scores.values()) / len(goals.goal_scores))
            if goals.goal_scores else None
        )
    elif goals.goal_scores:
        goal_score = round(sum(goals.goal_scores.values()) / len(goals.goal_scores))
        compatibility_score = goal_score
    else:
        goal_score = None
        compatibility_score = 100

    unknown_ingredients = sorted(
        set(safety.unknown_ingredients) | set(goals.unknown_ingredients)
    )

    return CompatibilityResult(
        compatibility_score=compatibility_score,
        safety_score=safety.safety_score,
        goal_score=goal_score,
        confidence=safety.confidence,
        detected_allergens=safety.detected_allergens,
        detected_restrictions=safety.detected_restrictions,
        goal_scores=goals.goal_scores,
        unassessed_goals=goals.unassessed_goals,
        unknown_ingredients=unknown_ingredients,
        warnings=safety.warnings,
        suggested_modifications=safety.suggested_modifications,
        questions_to_ask=safety.questions_to_ask,
    )
