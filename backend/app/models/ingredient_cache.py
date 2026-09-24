from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.database.connection import Base


class IngredientCache(Base):
    __tablename__ = "ingredient_cache"

    id = Column(Integer, primary_key=True, index=True)

    ingredient_name = Column(String, unique=True, index=True, nullable=False)

    found = Column(Boolean, nullable=False)

    health_labels = Column(JSONB, nullable=False, default=list)

    nutrients = Column(JSONB, nullable=False, default=dict)

    fetched_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
