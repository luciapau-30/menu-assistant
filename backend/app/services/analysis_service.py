from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.storage import save_image
from app.models.analysis import Analysis, AnalysisStatus, AnalysisType
from app.models.user import User
from app.schemas.extraction import ReportRequest


def create_analysis(
    db: Session, user: User, file: UploadFile, analysis_type: AnalysisType
) -> Analysis:
    image_url = save_image(file)

    analysis = Analysis(
        user_id=user.id,
        type=analysis_type,
        image_url=image_url,
        status=AnalysisStatus.UPLOADED,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


def get_analysis(db: Session, user: User, analysis_id: int) -> Analysis:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
        .first()
    )

    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis


def _claim_analysis(db: Session, user: User, analysis_id: int) -> Analysis:
    analysis = get_analysis(db, user, analysis_id)
    claimed = (
        db.query(Analysis)
        .filter(Analysis.id == analysis.id, Analysis.user_id == user.id,
                Analysis.status.in_([AnalysisStatus.UPLOADED, AnalysisStatus.FAILED]))
        .update({Analysis.status: AnalysisStatus.PROCESSING, Analysis.error_message: None},
                synchronize_session=False)
    )
    if not claimed:
        db.rollback()
        raise HTTPException(status_code=409, detail="Analysis is processing or already completed.")
    db.commit()
    db.refresh(analysis)
    return analysis


def _fail_analysis(db: Session, analysis: Analysis, message: str) -> Analysis:
    db.rollback()
    analysis.status = AnalysisStatus.FAILED
    analysis.error_message = message
    db.commit()
    db.refresh(analysis)
    return analysis


def extract_analysis(db: Session, user: User, analysis_id: int) -> Analysis:
    from app.llm.vision import ExtractionError, extract_image

    analysis = _claim_analysis(db, user, analysis_id)
    try:
        extraction = extract_image(analysis.image_url, analysis.type.value)
        analysis.extraction = extraction.model_dump()
        # UPLOADED plus extraction means ready for user review, not completed.
        analysis.status = AnalysisStatus.UPLOADED
        db.commit()
        db.refresh(analysis)
        return analysis
    except ExtractionError as exc:
        return _fail_analysis(db, analysis, str(exc))
    except Exception:
        return _fail_analysis(db, analysis, "Image extraction failed. Retry or enter ingredients manually.")


def complete_analysis(db: Session, user: User, analysis_id: int, request: ReportRequest) -> Analysis:
    from dataclasses import asdict

    from app.compatibility.models import MenuItemInput, UserProfileInput
    from app.services.compatibility_service import run_compatibility_check
    from app.services.profile_service import profile_to_response_data

    analysis = _claim_analysis(db, user, analysis_id)
    try:
        snapshot = profile_to_response_data(user)
        profile = UserProfileInput(**{key: value for key, value in snapshot.items() if key != "name"})
        reports = []
        for item in request.items:
            result = run_compatibility_check(db, user, MenuItemInput(item.name, item.ingredients), profile=profile)
            reports.append({"menu_item_name": item.name, "ingredients": item.ingredients, **asdict(result)})
        analysis.reports = reports
        analysis.profile_snapshot = snapshot
        analysis.status = AnalysisStatus.COMPLETED
        db.commit()
        db.refresh(analysis)
        return analysis
    except Exception:
        return _fail_analysis(db, analysis, "Report generation failed. Please retry.")
