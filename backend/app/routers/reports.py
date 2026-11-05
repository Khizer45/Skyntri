import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ProgressCheck, Report, SkinAnalysis, User
from app.dependencies import get_current_user
from app.schemas import ReportGenerateRequest, ReportOut
from app.services.pdf_report import generate_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a PDF report using the user's skin analysis and/or
    progress comparison data.

    If no analysis_id or progress_id is provided, the latest
    available record for the authenticated user is used.
    """

    # ---------------------------------------------------------
    # Get skin analysis
    # ---------------------------------------------------------

    analysis = None

    if payload.analysis_id:
        analysis = (
            db.query(SkinAnalysis)
            .filter(
                SkinAnalysis.id == payload.analysis_id,
                SkinAnalysis.user_id == current_user.id,
            )
            .first()
        )

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced analysis not found.",
            )
    else:
        analysis = (
            db.query(SkinAnalysis)
            .filter(
                SkinAnalysis.user_id == current_user.id,
            )
            .order_by(desc(SkinAnalysis.created_at))
            .first()
        )

    # ---------------------------------------------------------
    # Get progress comparison
    # ---------------------------------------------------------

    progress = None

    if payload.progress_id:
        progress = (
            db.query(ProgressCheck)
            .filter(
                ProgressCheck.id == payload.progress_id,
                ProgressCheck.user_id == current_user.id,
            )
            .first()
        )

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced progress check not found.",
            )
    else:
        progress = (
            db.query(ProgressCheck)
            .filter(
                ProgressCheck.user_id == current_user.id,
            )
            .order_by(desc(ProgressCheck.created_at))
            .first()
        )

    # ---------------------------------------------------------
    # Make sure there is something to put in the report
    # ---------------------------------------------------------

    if analysis is None and progress is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No skin analysis or progress data is available "
                "to generate a report."
            ),
        )

    # ---------------------------------------------------------
    # Create report database record
    # ---------------------------------------------------------

    report = Report(
        user_id=current_user.id,
        title=payload.title,
        file_path="",
        analysis_id=analysis.id if analysis else None,
        progress_id=progress.id if progress else None,
    )

    db.add(report)
    db.flush()

    # ---------------------------------------------------------
    # Generate PDF
    # ---------------------------------------------------------

    try:
        file_path = generate_report_pdf(
            current_user,
            report.id,
            payload.title,
            analysis,
            progress,
        )
    except Exception as exc:
        db.rollback()
        logging.getLogger("skyntri.reports").exception(
            "report_generation_failed", extra={"event": "report_generation_failed"}
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generation failed. Please try again.",
        ) from exc

    # ---------------------------------------------------------
    # Save generated PDF path
    # ---------------------------------------------------------

    report.file_path = str(file_path)

    db.commit()
    db.refresh(report)

    return report


@router.get(
    "",
    response_model=list[ReportOut],
)
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all reports belonging to the authenticated user.
    """

    return (
        db.query(Report)
        .filter(
            Report.user_id == current_user.id,
        )
        .order_by(desc(Report.created_at))
        .all()
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a generated PDF report belonging to the authenticated user.
    """

    report = (
        db.query(Report)
        .filter(
            Report.id == report_id,
            Report.user_id == current_user.id,
        )
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file is not available.",
        )

    file_path = Path(report.file_path)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file could not be found.",
        )

    safe_title = re.sub(r"[^A-Za-z0-9 _.-]+", "", report.title or "").strip()[:80]

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"{safe_title or 'skyntri-report'}.pdf",
        headers={"Cache-Control": "private, no-store"},
    )