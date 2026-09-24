from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.profile_service import profile_to_response_data, update_profile

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user)
):
    return profile_to_response_data(current_user)


@router.put("", response_model=ProfileResponse)
def put_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = update_profile(db, current_user, profile_data)

    return profile_to_response_data(updated_user)


@router.get("/options", response_model=dict[str, list[str]])
def get_profile_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.profile_service import CATEGORY_MODELS

    return {
        category: [row.name for row in db.query(model).order_by(model.name).all()]
        for category, model in CATEGORY_MODELS.items()
    }
