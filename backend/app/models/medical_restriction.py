from sqlalchemy import Column, ForeignKey, Integer, String, Table

from app.database.connection import Base

user_medical_restrictions = Table(
    "user_medical_restrictions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "medical_restriction_id",
        Integer,
        ForeignKey("medical_restrictions.id"),
        primary_key=True,
    ),
)


class MedicalRestriction(Base):
    __tablename__ = "medical_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
