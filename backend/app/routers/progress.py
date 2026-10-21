from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import ProgressCheck, User
from app.dependencies import get_current_user
from app.schemas import ProgressCheckOut
from app.services.progress import compute_progress_score
from app.services.uploads import save_upload

router = APIRouter(
    prefix="/progress",
    tags=["progress-checker"],
)


# ============================================================
# Helpers
# ============================================================

def _parse_observations(value: str | None) -> list[str]:
    """
    Safely convert stored observations JSON into a list.
    """

    if not value:
        return []

    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(decoded, list):
        return []

    return [
        str(item)
        for item in decoded
        if item is not None
    ]


def _delete_uploaded_file(
    image_url: str | None,
) -> None:
    """
    Delete an uploaded file belonging to the local uploads directory.

    This is used when progress analysis fails after an upload has
    already been saved.
    """

    if not image_url:
        return

    prefix = "/uploads/"

    if not image_url.startswith(prefix):
        return

    relative_path = image_url.removeprefix(prefix)

    if not relative_path:
        return

    upload_root = settings.upload_path.resolve()
    file_path = (
        settings.upload_path / relative_path
    ).resolve()

    try:
        file_path.relative_to(upload_root)
    except ValueError:
        return

    if file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            pass


def _serialize_progress(
    progress: ProgressCheck,
) -> dict:
    """
    Convert a ProgressCheck database object into a frontend-safe
    response dictionary.

    The database stores observations as JSON text, so it must be
    explicitly converted back into a Python list.
    """

    return {
        "id": progress.id,
        "before_image_url": progress.before_image_url,
        "after_image_url": progress.after_image_url,
        "status": progress.status,
        "score": progress.score,
        "observations": _parse_observations(
            progress.observations_json
        ),
        "created_at": progress.created_at,
    }


# ============================================================
# Create progress comparison
# ============================================================

@router.post(
    "",
    response_model=ProgressCheckOut,
    status_code=status.HTTP_201_CREATED,
)
def check_progress(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare before and after skin images using OpenCV.

    The images are stored under the progress upload directory and
    compared using visible redness, estimated affected-area pattern,
    and texture variation.

    The result is an AI/image-processing estimate and not a medical
    diagnosis or clinical measurement.
    """

    before_url: str | None = None
    after_url: str | None = None

    try:
        # ------------------------------------------------------
        # Save images
        # ------------------------------------------------------

        before_url = save_upload(
            before_image,
            "progress",
        )

        try:
            after_url = save_upload(
                after_image,
                "progress",
            )
        except Exception:
            _delete_uploaded_file(before_url)
            raise

        # ------------------------------------------------------
        # Convert public upload URLs to local file paths
        # ------------------------------------------------------

        before_relative = before_url.removeprefix(
            "/uploads/"
        )

        after_relative = after_url.removeprefix(
            "/uploads/"
        )

        before_path = (
            settings.upload_path / before_relative
        )

        after_path = (
            settings.upload_path / after_relative
        )

        # ------------------------------------------------------
        # Run OpenCV progress analysis
        # ------------------------------------------------------

        result = compute_progress_score(
            str(before_path),
            str(after_path),
        )

    except FileNotFoundError as exc:
        _delete_uploaded_file(before_url)
        _delete_uploaded_file(after_url)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Progress images could not be processed.",
        ) from exc

    except ValueError as exc:
        _delete_uploaded_file(before_url)
        _delete_uploaded_file(after_url)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except HTTPException:
        _delete_uploaded_file(before_url)
        _delete_uploaded_file(after_url)
        raise

    except Exception as exc:
        _delete_uploaded_file(before_url)
        _delete_uploaded_file(after_url)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Progress analysis failed.",
        ) from exc

    # ========================================================
    # Store result
    # ========================================================

    progress = ProgressCheck(
        user_id=current_user.id,
        before_image_url=before_url,
        after_image_url=after_url,
        status=result["status"],
        score=result["score"],
        observations_json=json.dumps(
            result.get(
                "observations",
                [],
            ),
            ensure_ascii=False,
        ),
    )

    try:
        db.add(progress)
        db.commit()
        db.refresh(progress)

    except Exception as exc:
        db.rollback()

        _delete_uploaded_file(before_url)
        _delete_uploaded_file(after_url)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the progress result.",
        ) from exc

    return _serialize_progress(progress)


# ============================================================
# Progress history
# ============================================================

@router.get(
    "",
    response_model=list[ProgressCheckOut],
)
def list_progress_checks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all progress checks belonging to the authenticated user.

    Results are returned newest first.
    """

    progress_checks = (
        db.query(ProgressCheck)
        .filter(
            ProgressCheck.user_id == current_user.id
        )
        .order_by(
            desc(ProgressCheck.created_at)
        )
        .all()
    )

    return [
        _serialize_progress(progress)
        for progress in progress_checks
    ]


# ============================================================
# Progress summary / trend data
# ============================================================

@router.get("/summary")
def get_progress_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return lightweight progress trend data for the frontend.

    This endpoint is intended for charts, weekly progress cards,
    and improvement/deterioration summaries.
    """

    progress_checks = (
        db.query(ProgressCheck)
        .filter(
            ProgressCheck.user_id == current_user.id
        )
        .order_by(
            ProgressCheck.created_at.asc()
        )
        .all()
    )

    improved = 0
    deteriorated = 0
    unchanged = 0

    timeline = []

    for progress in progress_checks:
        if progress.status == "Improved":
            improved += 1
        elif progress.status == "Deteriorated":
            deteriorated += 1
        else:
            unchanged += 1

        timeline.append(
            {
                "id": progress.id,
                "score": progress.score,
                "status": progress.status,
                "created_at": progress.created_at,
            }
        )

    total = len(progress_checks)

    average_score = (
        round(
            sum(
                float(progress.score)
                for progress in progress_checks
            ) / total,
            1,
        )
        if total
        else None
    )

    return {
        "total_checks": total,
        "improved_count": improved,
        "deteriorated_count": deteriorated,
        "no_significant_change_count": unchanged,
        "average_score": average_score,
        "timeline": timeline,
    }


# ============================================================
# Single progress record
# ============================================================

@router.get(
    "/{progress_id}",
)
def get_progress_check(
    progress_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return one progress comparison belonging to the authenticated user.
    """

    progress = (
        db.query(ProgressCheck)
        .filter(
            ProgressCheck.id == progress_id,
            ProgressCheck.user_id == current_user.id,
        )
        .first()
    )

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress check not found.",
        )

    return _serialize_progress(progress)