import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, JSON

from app.database.connection import Base


class AnalysisType(str, enum.Enum):
    MENU = "MENU"
    NUTRITION_LABEL = "NUTRITION_LABEL"
    INGREDIENT_LIST = "INGREDIENT_LIST"


class AnalysisStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    type = Column(Enum(AnalysisType), nullable=False)

    image_url = Column(String, nullable=False)

    extraction = Column(JSON, nullable=True)
    reports = Column(JSON, nullable=True)
    profile_snapshot = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)

    status = Column(
        Enum(AnalysisStatus),
        nullable=False,
        default=AnalysisStatus.UPLOADED,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
