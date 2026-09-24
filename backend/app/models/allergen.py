from sqlalchemy import Column, ForeignKey, Integer, String, Table

from app.database.connection import Base

user_allergens = Table(
    "user_allergens",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("allergen_id", Integer, ForeignKey("allergens.id"), primary_key=True),
)


class Allergen(Base):
    __tablename__ = "allergens"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
