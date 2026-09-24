from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.analysis import AnalysisType
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import create_analysis, get_analysis, extract_analysis, complete_analysis
from app.schemas.extraction import ReportRequest

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/upload", response_model=AnalysisResponse)
def upload_analysis(
    image: UploadFile = File(...),
    type: AnalysisType = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = create_analysis(db, current_user, image, type)

    return analysis_response(analysis)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, current_user, analysis_id)

    return analysis_response(analysis)


def analysis_response(analysis) -> AnalysisResponse:
    return AnalysisResponse(
        analysis_id=analysis.id, status=analysis.status,
        extraction=analysis.extraction, reports=analysis.reports,
        profile_snapshot=analysis.profile_snapshot, error_message=analysis.error_message,
    )


@router.post("/{analysis_id}/extract", response_model=AnalysisResponse)
def extract_uploaded_image(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analysis_response(extract_analysis(db, current_user, analysis_id))


@router.post("/{analysis_id}/report", response_model=AnalysisResponse)
def generate_reviewed_report(
    analysis_id: int,
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analysis_response(complete_analysis(db, current_user, analysis_id, request))
