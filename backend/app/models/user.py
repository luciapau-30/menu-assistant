from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.allergen import user_allergens
from app.models.dietary_style import user_dietary_styles
from app.models.medical_restriction import user_medical_restrictions
from app.models.nutrition_goal import user_nutrition_goals


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    allergens = relationship(
        "Allergen", secondary=user_allergens, backref="users"
    )
    #to get from User to Allergen, go through the user_allergens table.

    medical_restrictions = relationship(
        "MedicalRestriction", secondary=user_medical_restrictions, backref="users"
    )

    dietary_styles = relationship(
        "DietaryStyle", secondary=user_dietary_styles, backref="users"
    )

    nutrition_goals = relationship(
        "NutritionGoal", secondary=user_nutrition_goals, backref="users"
    )