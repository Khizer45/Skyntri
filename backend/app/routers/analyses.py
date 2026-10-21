from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import SkinAnalysis, User
from app.dependencies import get_current_user
from app.schemas import (
    SkinAnalysisAnalyzeOut,
    SkinAnalysisCreate,
    SkinAnalysisOut,
)
from app.services.skin_analysis import analyze_skin_image
from app.services.uploads import save_upload


router = APIRouter(
    prefix="/analyses",
    tags=["skin-analysis"],
)


# ============================================================
# Constants
# ============================================================

VALID_SEVERITY_LEVELS = {
    "Low",
    "Moderate",
    "High",
}


# ============================================================
# Helper functions
# ============================================================

def _remove_uploaded_file(image_path: Path) -> None:
    """
    Remove an uploaded image when the analysis pipeline or database
    persistence fails.

    Cleanup errors are intentionally ignored because they should not
    replace the original application error.
    """
    try:
        if image_path.exists():
            image_path.unlink()
    except OSError:
        pass


def _build_local_image_path(image_url: str) -> Path:
    """
    Convert an internal /uploads/... URL into the corresponding
    local filesystem path.

    Example:
        /uploads/analyses/file.jpg

    becomes:
        <configured upload directory>/analyses/file.jpg
    """
    prefix = "/uploads/"

    if not image_url.startswith(prefix):
        raise ValueError("Invalid upload URL.")

    relative_path = image_url.removeprefix(prefix)

    if not relative_path:
        raise ValueError("Invalid upload URL.")

    return settings.upload_path / relative_path


def _safe_analysis_error(exc: Exception) -> str:
    """
    Convert internal analysis errors into safe API messages.

    TensorFlow/model paths/internal implementation details should not
    be exposed to the frontend.
    """
    if isinstance(exc, FileNotFoundError):
        return (
            "The uploaded image or required analysis resource "
            "could not be found."
        )

    if isinstance(exc, ValueError):
        message = str(exc).strip()

        if message:
            return message

        return (
            "The uploaded image could not be processed. "
            "Please try another clear image."
        )

    return (
        "Skin analysis could not be completed. "
        "Please try again with a clear skin image."
    )


def _normalize_severity(value: object) -> str:
    """
    Ensure the AI service returns one of the severity levels supported
    by the current database/schema.
    """
    severity = str(value or "Low").strip().title()

    if severity not in VALID_SEVERITY_LEVELS:
        return "Low"

    return severity


def _build_explanation(
    conditions: list[str],
    severity_level: str,
) -> str:
    """
    Build a concise database-friendly explanation.

    This explanation describes an AI-estimated visible-pattern result,
    not a medical diagnosis.
    """
    if conditions:
        condition_text = ", ".join(conditions)

        return (
            "The AI estimated the following visible skin patterns: "
            f"{condition_text}. "
            f"The AI-estimated visible-pattern severity is "
            f"{severity_level}. "
            "This is not a medical diagnosis."
        )

    return (
        "The AI did not identify a specific visible skin condition "
        "from the analyzed image. "
        f"The AI-estimated visible-pattern severity is "
        f"{severity_level}. "
        "This is not a medical diagnosis."
    )


# ============================================================
# AI skin analysis
# ============================================================

@router.post(
    "/analyze",
    response_model=SkinAnalysisAnalyzeOut,
    status_code=status.HTTP_201_CREATED,
)
def analyze_uploaded_skin_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Complete authenticated AI skin-analysis endpoint.

    Flow:

        React
          ↓
        Upload image
          ↓
        save_upload()
          ↓
        Dataset 3 preprocessing
          ↓
        Dataset 3 multi-label inference
          ↓
        Optimized thresholds
          ↓
        Detected conditions
          ↓
        AI-estimated visible-pattern severity
          ↓
        Recommendations
          ↓
        Save SkinAnalysis in database
          ↓
        Return clean frontend response

    The frontend receives:
        - analysis_id
        - image_url
        - conditions
        - recommendations
        - confidence_score
        - severity_level
        - disclaimer

    Internal model details such as:
        - model name
        - thresholds
        - raw probabilities
        - internal severity evidence

    are NOT returned.
    """

    image_url: str | None = None
    image_path: Path | None = None

    # ========================================================
    # 1. Validate basic upload information
    # ========================================================

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a skin image.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file has no filename.",
        )

    # ========================================================
    # 2. Save uploaded image
    # ========================================================

    try:
        image_url = save_upload(
            file,
            "analyses",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image could not be uploaded.",
        ) from exc

    # ========================================================
    # 3. Resolve local image path
    # ========================================================

    try:
        image_path = _build_local_image_path(
            image_url
        )

    except ValueError as exc:
        if image_path is not None:
            _remove_uploaded_file(image_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The uploaded image path could not be resolved.",
        ) from exc

    # ========================================================
    # 4. Verify image exists
    # ========================================================

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The uploaded image could not be found.",
        )

    # ========================================================
    # 5. Run Dataset 3 AI analysis
    # ========================================================

    try:
        result = analyze_skin_image(
            image_path
        )

    except Exception as exc:
        _remove_uploaded_file(image_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_safe_analysis_error(exc),
        ) from exc

    # ========================================================
    # 6. Extract clean service result
    # ========================================================

    conditions_raw = result.get(
        "conditions",
        [],
    )

    if not isinstance(conditions_raw, list):
        conditions = []

    else:
        conditions = [
            str(condition).strip()
            for condition in conditions_raw
            if str(condition).strip()
        ]

    # Remove duplicates while preserving order.
    conditions = list(
        dict.fromkeys(conditions)
    )

    recommendations = result.get(
        "recommendations",
        {},
    )

    if not isinstance(recommendations, dict):
        recommendations = {}

    # Current schema/database uses percentage confidence.
    confidence_score = result.get(
        "confidence_score",
        0.0,
    )

    try:
        confidence_score = float(
            confidence_score
        )

    except (TypeError, ValueError):
        confidence_score = 0.0

    confidence_score = max(
        0.0,
        min(
            100.0,
            confidence_score,
        ),
    )

    severity_level = _normalize_severity(
        result.get(
            "severity_level",
            "Low",
        )
    )

    disclaimer = str(
        result.get(
            "disclaimer",
            (
                "This result is an AI-estimated assessment of visible "
                "skin patterns, not a medical diagnosis."
            ),
        )
    ).strip()

    if not disclaimer:
        disclaimer = (
            "This result is an AI-estimated assessment of visible "
            "skin patterns, not a medical diagnosis."
        )

    # ========================================================
    # 7. Build DB condition summary
    # ========================================================

    if conditions:
        predicted_condition = ", ".join(
            conditions
        )
    else:
        predicted_condition = (
            "No specific visible condition detected"
        )

    explanation = _build_explanation(
        conditions,
        severity_level,
    )

    # ========================================================
    # 8. Create database record
    # ========================================================

    analysis = SkinAnalysis(
        user_id=current_user.id,
        image_url=image_url,
        predicted_condition=predicted_condition,
        confidence_score=confidence_score,
        severity_level=severity_level,
        explanation=explanation,
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    except Exception as exc:
        db.rollback()

        _remove_uploaded_file(image_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The skin analysis result could not be saved.",
        ) from exc

    # ========================================================
    # 9. Return ONLY public API fields
    # ========================================================

    return SkinAnalysisAnalyzeOut(
        analysis_id=analysis.id,
        image_url=image_url,
        conditions=conditions,
        recommendations=recommendations,
        confidence_score=confidence_score,
        severity_level=severity_level,
        disclaimer=disclaimer,
    )


# ============================================================
# Manual analysis result endpoint
# ============================================================

@router.post(
    "",
    response_model=SkinAnalysisOut,
    status_code=status.HTTP_201_CREATED,
)
def save_analysis_result(
    payload: SkinAnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save an already-generated analysis result.

    This endpoint is preserved for compatibility with the existing
    backend.

    Normal frontend AI analysis should use:

        POST /analyses/analyze
    """

    severity_level = _normalize_severity(
        payload.severity_level
    )

    analysis = SkinAnalysis(
        user_id=current_user.id,
        image_url=payload.image_url,
        predicted_condition=payload.predicted_condition,
        confidence_score=payload.confidence_score,
        severity_level=severity_level,
        explanation=payload.explanation,
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The analysis result could not be saved.",
        ) from exc

    return analysis


# ============================================================
# Analysis history
# ============================================================

@router.get(
    "",
    response_model=list[SkinAnalysisOut],
)
def list_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return only the authenticated user's analysis history.
    """

    return (
        db.query(SkinAnalysis)
        .filter(
            SkinAnalysis.user_id == current_user.id
        )
        .order_by(
            desc(SkinAnalysis.created_at)
        )
        .all()
    )


# ============================================================
# Single analysis
# ============================================================

@router.get(
    "/{analysis_id}",
    response_model=SkinAnalysisOut,
)
def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return one analysis belonging to the authenticated user.

    User isolation is enforced through BOTH:
        - analysis ID
        - current user's ID
    """

    analysis = (
        db.query(SkinAnalysis)
        .filter(
            SkinAnalysis.id == analysis_id,
            SkinAnalysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    return analysis