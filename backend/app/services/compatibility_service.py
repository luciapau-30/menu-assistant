from sqlalchemy.orm import Session

from app.compatibility.goals import check_nutrition_goals
from app.compatibility.models import (
    CompatibilityResult,
    GoalResult,
    MenuItemInput,
    SafetyResult,
    UserProfileInput,
)
from app.compatibility.safety import check_safety
from app.compatibility.scoring import combine_scores
from app.llm.questions import generate_questions_with_llm
from app.models.user import User


def build_profile_input(user: User) -> UserProfileInput:
    return UserProfileInput(
        allergens=[a.name for a in user.allergens],
        medical_restrictions=[m.name for m in user.medical_restrictions],
        dietary_styles=[d.name for d in user.dietary_styles],
        nutrition_goals=[n.name for n in user.nutrition_goals],
    )


def run_safety_check(
    db: Session, user: User, menu_item: MenuItemInput
) -> SafetyResult:
    profile = build_profile_input(user)

    return check_safety(db, menu_item, profile)


def run_goal_check(db: Session, user: User, menu_item: MenuItemInput) -> GoalResult:
    profile = build_profile_input(user)

    return check_nutrition_goals(db, menu_item, profile)


def run_compatibility_check(
    db: Session, user: User, menu_item: MenuItemInput,
    *, profile: UserProfileInput | None = None,
) -> CompatibilityResult:
    profile = profile if profile is not None else build_profile_input(user)

    safety_result = check_safety(db, menu_item, profile)
    goal_result = check_nutrition_goals(db, menu_item, profile)

    user_concerns = sorted(
        {*profile.allergens, *profile.medical_restrictions} - {"None"}
    )
    llm_questions = generate_questions_with_llm(
        menu_item.name, safety_result.unknown_ingredients, user_concerns
    )
    if llm_questions is not None:
        safety_result.questions_to_ask = llm_questions
    # else: keep the deterministic questions_to_ask already set by
    # check_safety -- the LLM is an enhancement, not a requirement.

    return combine_scores(safety_result, goal_result)
