from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
from app.services import app_settings, disease_screening, rate_limit
from app.services.image_gate import RETAKE_GUIDANCE, assess_image
from app.services.skin_analysis import InferenceBusyError, analyze_skin_image, model_artifact_available
from app.services.uploads import delete_upload, resolve_upload_url, save_upload

logger = logging.getLogger("skyntri.analysis")


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
# Analysis tracks (Model A / Model B)
# ============================================================

TRACK_FACIAL = "facial_concerns"
TRACK_DISEASE = "disease_screening"

TRACK_LABELS = {
    TRACK_FACIAL: "Facial skin concerns",
    TRACK_DISEASE: "Skin disease screening support",
}

TRACK_DESCRIPTIONS = {
    TRACK_FACIAL: (
        "Acne, blackheads, dark spots, pores, wrinkles, oiliness, dryness, "
        "redness and eye bags on the face."
    ),
    TRACK_DISEASE: (
        "Patterns such as eczema, psoriasis, fungal infection or hives on the "
        "face or body, and a referral flag for lesions that need a doctor."
    ),
}


def disease_track_available(db: Session | None = None) -> bool:
    """
    Model B needs its model files AND the switch to be on. The switch is the
    administrator's setting when one was saved (Admin panel -> Settings),
    otherwise DISEASE_SCREENING_ENABLED from the environment.
    """
    override = app_settings.get_optional_bool(db, "disease_screening_enabled") if db is not None else None
    if override is None:
        return disease_screening.is_available()
    return override and disease_screening.model_files_present()


def available_tracks(db: Session | None = None) -> set[str]:
    """
    Model A is available when its trained file is installed in backend/models/.
    Model B only when its model files are installed AND screening is switched
    on, which should happen only after dataset, external-validation and
    dermatology review (SEC-MED-003).
    """
    tracks = set()
    if model_artifact_available():
        tracks.add(TRACK_FACIAL)
    if disease_track_available(db):
        tracks.add(TRACK_DISEASE)
    return tracks


def _unavailable_reason(track: str) -> str:
    if track == TRACK_FACIAL:
        return "The facial analysis model has not been installed yet."
    if not disease_screening.model_files_present():
        return "The skin disease model has not been installed yet."
    return "Skin disease screening is switched off. An administrator can turn it on after clinical review."


@router.get("/tracks")
def list_tracks(db: Session = Depends(get_db)):
    """Public description of the analysis tracks and whether each is available."""
    available = available_tracks(db)
    return [
        {
            "id": track,
            "label": TRACK_LABELS[track],
            "description": TRACK_DESCRIPTIONS[track],
            "available": track in available,
            "reason": None if track in available else _unavailable_reason(track),
        }
        for track in (TRACK_FACIAL, TRACK_DISEASE)
    ]


def _abstain(detail: dict) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
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
    track: str = Form(default=TRACK_FACIAL),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Staged, abstaining skin-analysis pipeline (ML-01):

        1. rate limit + track check
        2. secure upload validation and decoding (save_upload)
        3. image quality + skin/non-skin eligibility + facial scope
           (image_gate.assess_image)            -> abstain if not accepted
        4. Model A inference with per-class thresholds
                                                -> abstain if uncertain
        5. persist result with track, model and gate versions

    Rejected images are deleted immediately and never receive condition
    labels. Abstentions return HTTP 422 with a reason code and guidance.
    """
    track = (track or TRACK_FACIAL).strip().lower()

    if track not in TRACK_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown analysis type.",
        )

    if track == TRACK_FACIAL and not model_artifact_available():
        raise _abstain(
            {
                "code": "model_not_installed",
                "status": "unavailable",
                "message": (
                    "Facial skin analysis is not ready yet: the trained model has not "
                    "been installed. Please try again later."
                ),
                "guidance": [],
            }
        )

    if track not in available_tracks(db):
        raise _abstain(
            {
                "code": "track_not_available",
                "status": "unavailable",
                "message": (
                    "Skin disease screening support is not available yet. "
                    "It will only be enabled after clinical review and "
                    "independent validation. If you are worried about a "
                    "skin condition or a changing mole or lesion, please "
                    "see a dermatologist or doctor."
                ),
                "guidance": [],
            }
        )

    rate_limit.enforce(
        db,
        "analysis",
        current_user.id,
        settings.analysis_per_hour,
        message="Analysis limit reached. Please try again later.",
    )

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a skin image.",
        )

    image_url = save_upload(file, "analyses")
    image_path = resolve_upload_url(image_url)

    if image_path is None or not image_path.exists():
        delete_upload(image_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The uploaded image could not be processed.",
        )

    # --------------------------------------------------------
    # Eligibility gate - the condition model is NOT called for
    # rejected or uncertain images.
    # --------------------------------------------------------
    gate = assess_image(image_path, track=track)

    if not gate.accepted:
        delete_upload(image_url)
        logger.info(
            "analysis_abstained",
            extra={
                "event": "analysis_abstained",
                "stage": "input_gate",
                "reason": gate.reason_code,
                "gate_version": gate.gate_version,
                "track": track,
            },
        )
        raise _abstain(gate.public_detail())

    try:
        if track == TRACK_DISEASE:
            result = disease_screening.screen_image(image_path)
        else:
            result = analyze_skin_image(image_path)
    except InferenceBusyError as exc:
        delete_upload(image_url)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The analysis service is busy. Please try again in a moment.",
            headers={"Retry-After": "10"},
        ) from exc
    except Exception as exc:
        delete_upload(image_url)
        logger.exception("analysis_failed", extra={"event": "analysis_failed"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_safe_analysis_error(exc),
        ) from exc

    if result.get("status") == "uncertain":
        delete_upload(image_url)
        logger.info(
            "analysis_abstained",
            extra={
                "event": "analysis_abstained",
                "stage": "model_uncertainty",
                "reason": "model_uncertain",
                "gate_version": gate.gate_version,
                "model_version": result.get("model_version"),
                "track": track,
            },
        )
        raise _abstain(
            {
                "code": "model_uncertain",
                "status": "uncertain",
                "message": "We cannot confidently analyze this image. Please upload another photo.",
                "guidance": RETAKE_GUIDANCE,
                "gate_version": gate.gate_version,
            }
        )

    conditions_raw = result.get("conditions", [])
    conditions = (
        [str(c).strip() for c in conditions_raw if str(c).strip()]
        if isinstance(conditions_raw, list)
        else []
    )
    conditions = list(dict.fromkeys(conditions))

    recommendations = result.get("recommendations", {})
    if not isinstance(recommendations, dict):
        recommendations = {}

    try:
        confidence_score = float(result.get("confidence_score", 0.0))
    except (TypeError, ValueError):
        confidence_score = 0.0
    confidence_score = max(0.0, min(100.0, confidence_score))

    severity_level = _normalize_severity(result.get("severity_level", "Low"))

    disclaimer = str(result.get("disclaimer") or "").strip() or (
        "This result is an AI-estimated assessment of visible "
        "skin patterns, not a medical diagnosis."
    )

    if conditions:
        predicted_condition = ", ".join(conditions)
    elif track == TRACK_DISEASE:
        predicted_condition = "No supported disease pattern recognised (not a medical all-clear)"
    else:
        predicted_condition = "No specific visible condition detected"

    model_version = str(result.get("model_version") or settings.facial_model_version)

    analysis = SkinAnalysis(
        user_id=current_user.id,
        image_url=image_url,
        predicted_condition=predicted_condition,
        confidence_score=confidence_score,
        severity_level=severity_level,
        explanation=_build_explanation(conditions, severity_level),
        analysis_track=track,
        model_version=model_version,
        gate_version=gate.gate_version,
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except Exception as exc:
        db.rollback()
        delete_upload(image_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The skin analysis result could not be saved.",
        ) from exc

    logger.info(
        "analysis_completed",
        extra={
            "event": "analysis_completed",
            "track": track,
            "model_version": model_version,
            "gate_version": gate.gate_version,
            "condition_count": len(conditions),
        },
    )

    return SkinAnalysisAnalyzeOut(
        analysis_id=analysis.id,
        image_url=image_url,
        conditions=conditions,
        recommendations=recommendations,
        confidence_score=confidence_score,
        severity_level=severity_level,
        disclaimer=disclaimer,
        analysis_track=track,
        analysis_track_label=TRACK_LABELS[track],
        model_version=model_version,
        gate_version=gate.gate_version,
        referral=bool(result.get("referral", False)),
        summary=result.get("summary"),
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

    # A client must not be able to attach (and later receive a signed URL
    # for) another user's private file.
    image_url = payload.image_url
    if image_url and (image_url.startswith("/uploads/") or image_url.startswith("/files/")):
        owned = (
            db.query(SkinAnalysis.id)
            .filter(
                SkinAnalysis.user_id == current_user.id,
                SkinAnalysis.image_url == image_url,
            )
            .first()
        )
        if not owned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The referenced image is not available.",
            )
    elif image_url and not image_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image reference.",
        )

    analysis = SkinAnalysis(
        user_id=current_user.id,
        image_url=image_url,
        analysis_track="facial_concerns",
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