from pydantic import BaseModel

from app.models.analysis import AnalysisStatus, AnalysisType
from app.schemas.extraction import Extraction
from app.schemas.compatibility import CompatibilityCheckResponse
from app.schemas.profile import ProfileResponse


class AnalysisResponse(BaseModel):
    analysis_id: int
    status: AnalysisStatus
    extraction: Extraction | None = None
    reports: list[CompatibilityCheckResponse] | None = None
    profile_snapshot: ProfileResponse | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True
