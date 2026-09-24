from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.compatibility.models import MenuItemInput
from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.schemas.compatibility import (
    CompatibilityCheckRequest,
    CompatibilityCheckResponse,
)
from app.services.compatibility_service import run_compatibility_check

router = APIRouter(prefix="/api/v1/compatibility", tags=["compatibility"])


@router.post("/check", response_model=CompatibilityCheckResponse)
def check_compatibility(
    request_data: CompatibilityCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    menu_item = MenuItemInput(
        name=request_data.menu_item_name, ingredients=request_data.ingredients
    )
    result = run_compatibility_check(db, current_user, menu_item)

    return CompatibilityCheckResponse(
        menu_item_name=request_data.menu_item_name,
        ingredients=request_data.ingredients,
        compatibility_score=result.compatibility_score,
        safety_score=result.safety_score,
        goal_score=result.goal_score,
        confidence=result.confidence,
        detected_allergens=result.detected_allergens,
        detected_restrictions=result.detected_restrictions,
        goal_scores=result.goal_scores,
        unassessed_goals=result.unassessed_goals,
        unknown_ingredients=result.unknown_ingredients,
        warnings=result.warnings,
        suggested_modifications=result.suggested_modifications,
        questions_to_ask=result.questions_to_ask,
    )
