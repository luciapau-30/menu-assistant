from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.allergen import Allergen
from app.models.dietary_style import DietaryStyle
from app.models.medical_restriction import MedicalRestriction
from app.models.nutrition_goal import NutritionGoal
from app.models.user import User
from app.schemas.profile import ProfileUpdate

CATEGORY_MODELS = {
    "allergens": Allergen,
    "medical_restrictions": MedicalRestriction,
    "dietary_styles": DietaryStyle,
    "nutrition_goals": NutritionGoal,
}


def _resolve_selection(db: Session, model, names: list[str]):
    if not names:
        return []

    rows = db.query(model).filter(model.name.in_(names)).all()

    found_names = {row.name for row in rows}
    unknown_names = set(names) - found_names

    if unknown_names:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown {model.__tablename__} value(s): {sorted(unknown_names)}",
        )

    return rows


def update_profile(db: Session, user: User, profile_data: ProfileUpdate) -> User:
    for field, model in CATEGORY_MODELS.items():
        names = getattr(profile_data, field)
        setattr(user, field, _resolve_selection(db, model, names))

    db.commit()
    db.refresh(user)

    return user


def profile_to_response_data(user: User) -> dict:
    return {
        "name": user.name,
        "allergens": [a.name for a in user.allergens],
        "medical_restrictions": [m.name for m in user.medical_restrictions],
        "dietary_styles": [d.name for d in user.dietary_styles],
        "nutrition_goals": [n.name for n in user.nutrition_goals],
    }
