from sqlalchemy import Column, ForeignKey, Integer, String, Table

from app.database.connection import Base

user_nutrition_goals = Table(
    "user_nutrition_goals",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "nutrition_goal_id",
        Integer,
        ForeignKey("nutrition_goals.id"),
        primary_key=True,
    ),
)


class NutritionGoal(Base):
    __tablename__ = "nutrition_goals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
