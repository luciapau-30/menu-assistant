from sqlalchemy import Column, ForeignKey, Integer, String, Table

from app.database.connection import Base

user_dietary_styles = Table(
    "user_dietary_styles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "dietary_style_id",
        Integer,
        ForeignKey("dietary_styles.id"),
        primary_key=True,
    ),
)


class DietaryStyle(Base):
    __tablename__ = "dietary_styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
