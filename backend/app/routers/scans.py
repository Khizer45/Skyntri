from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import IngredientScan, User
from app.dependencies import get_current_user
from app.schemas import IngredientScanOut
from app.services.ingredient_matching import (
    match_ingredients,
    personalize_for_skin_type,
)
from app.services.ocr import (
    extract_ingredient_tokens,
    extract_text,
)
from app.services import rate_limit
from app.services.uploads import save_upload


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/scans",
    tags=["ingredient-scanner"],
)


# ---------------------------------------------------------------------------
# Safety score
# ---------------------------------------------------------------------------

def _calculate_safety_score(
    matched_ingredients: list[dict],
) -> int:
    """
    Calculate an overall product safety score from 1-5.

    Lower ingredient scores receive stronger influence so that one
    potentially problematic ingredient is not hidden by many neutral ones.
    """
    if not matched_ingredients:
        return 1

    scores = [
        max(
            1,
            min(
                5,
                int(
                    item["ingredient"].safety_score
                    or 1
                ),
            ),
        )
        for item in matched_ingredients
    ]

    scores.sort()

    if len(scores) == 1:
        return scores[0]

    lowest = scores[0]
    second_lowest = scores[1]

    average = sum(scores) / len(scores)

    weighted = (
        lowest * 0.50
        + second_lowest * 0.25
        + average * 0.25
    )

    return max(
        1,
        min(
            5,
            round(weighted),
        ),
    )


def _safety_label(score: int) -> str:
    """Convert numeric safety score into frontend label."""
    if score >= 5:
        return "Very Good"

    if score >= 4:
        return "Good"

    if score >= 3:
        return "Moderate"

    if score >= 2:
        return "Caution"

    return "High Caution"


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _safe_json_list(value: str | None) -> list:
    """Safely decode a JSON list."""
    if not value:
        return []

    try:
        decoded = json.loads(value)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return []

    return (
        decoded
        if isinstance(decoded, list)
        else []
    )


# ---------------------------------------------------------------------------
# Ingredient serialization
# ---------------------------------------------------------------------------

def _serialize_ingredient(
    item: dict,
    user_skin_type: str | None,
) -> dict:
    """Convert matched ingredient to frontend-safe JSON."""
    ingredient = item["ingredient"]

    suitable_skin_types = _safe_json_list(
        ingredient.suitable_skin_types_json
    )

    avoid_skin_types = _safe_json_list(
        ingredient.avoid_skin_types_json
    )

    uses = _safe_json_list(
        ingredient.uses_json
    )

    warning = personalize_for_skin_type(
        ingredient,
        user_skin_type,
    )

    return {
        "token": item["token"],
        "name": ingredient.name,
        "inci_name": ingredient.inci_name,
        "category": ingredient.category,
        "function": ingredient.function,
        "uses": uses,
        "safety_status": ingredient.safety_status,
        "safety_score": ingredient.safety_score,
        "match_score": item["score"],
        "suitable_skin_types": suitable_skin_types,
        "avoid_skin_types": avoid_skin_types,
        "when_to_use": ingredient.when_to_use,
        "precautions": ingredient.precautions,
        "personalized_warning": warning,
    }


# ---------------------------------------------------------------------------
# Scan details
# ---------------------------------------------------------------------------

def _build_scan_details(
    matched: list[dict],
    unmatched: list[str],
    user_skin_type: str | None,
) -> dict:
    """Build JSON data stored in IngredientScan.details_json."""
    serialized = [
        _serialize_ingredient(
            item,
            user_skin_type,
        )
        for item in matched
    ]

    safety_score = _calculate_safety_score(
        matched
    )

    beneficial_count = sum(
        1
        for item in matched
        if item["ingredient"].safety_status
        == "Beneficial"
    )

    caution_count = (
        len(matched)
        - beneficial_count
    )

    personalized_warnings = [
        item["personalized_warning"]
        for item in serialized
        if item["personalized_warning"]
    ]

    return {
        "matched_ingredients": serialized,
        "unmatched_ingredients": unmatched,
        "personalized_warnings": personalized_warnings,
        "safety_score": safety_score,
        "safety_label": _safety_label(
            safety_score
        ),
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

def _build_response(
    scan: IngredientScan,
) -> dict:
    """Build stable frontend response."""
    try:
        details = json.loads(
            scan.details_json or "{}"
        )
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        details = {}

    return {
        "id": scan.id,
        "image_url": scan.image_url,
        "product_name": scan.product_name,
        "total_ingredients": scan.total_ingredients,
        "beneficial_count": scan.beneficial_count,
        "caution_count": scan.caution_count,
        "safety_score": scan.safety_score,
        "safety_label": details.get(
            "safety_label",
            _safety_label(
                scan.safety_score
            ),
        ),
        "matched_ingredients": details.get(
            "matched_ingredients",
            [],
        ),
        "unmatched_ingredients": details.get(
            "unmatched_ingredients",
            [],
        ),
        "personalized_warnings": details.get(
            "personalized_warnings",
            [],
        ),
        "created_at": scan.created_at,
    }


# ---------------------------------------------------------------------------
# Create scan
# ---------------------------------------------------------------------------

@router.post(
    "/scan",
    response_model=IngredientScanOut,
    status_code=status.HTTP_201_CREATED,
)
def scan_ingredients(
    image: UploadFile | None = File(
        default=None
    ),
    ingredients_text: str | None = Form(
        default=None
    ),
    product_name: str | None = Form(
        default=None
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Analyze skincare product ingredients.

    Supports:

    1. OCR image upload
    2. Manual ingredient text
    3. OCR + manual correction/supplement
    """
    rate_limit.enforce(
        db,
        "scan",
        current_user.id,
        settings.scan_per_hour,
        message="Scan limit reached. Please try again later.",
    )

    if image is None and not ingredients_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Provide an ingredient image or "
                "enter ingredients manually."
            ),
        )

    saved_image_url: str | None = None
    saved_path: Path | None = None

    tokens: list[str] = []

    try:
        # ---------------------------------------------------------------
        # OCR mode
        # ---------------------------------------------------------------
        if image is not None:
            saved_image_url = save_upload(
                image,
                subfolder="ingredients_scans",
            )

            relative_path = Path(
                saved_image_url.replace(
                    "/uploads/",
                    "",
                    1,
                )
            )

            saved_path = (
                settings.upload_path
                / relative_path
            )

            raw_text = extract_text(
                saved_path
            )

            tokens = extract_ingredient_tokens(
                raw_text
            )

        # ---------------------------------------------------------------
        # Manual mode / OCR correction
        # ---------------------------------------------------------------
        if ingredients_text:
            manual_tokens = (
                extract_ingredient_tokens(
                    ingredients_text
                )
            )

            if manual_tokens:
                existing = {
                    token.casefold()
                    for token in tokens
                }

                for token in manual_tokens:
                    normalized = token.casefold()

                    if normalized not in existing:
                        tokens.append(token)
                        existing.add(normalized)

        # ---------------------------------------------------------------
        # No extracted ingredients
        # ---------------------------------------------------------------
        if not tokens:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "No ingredient names could be "
                    "extracted. Please upload a clearer "
                    "label or enter the ingredient list "
                    "manually."
                ),
            )

        # ---------------------------------------------------------------
        # Database matching
        # ---------------------------------------------------------------
        result = match_ingredients(
            tokens,
            db,
        )

        matched = result["matched"]
        unmatched = result["unmatched"]

        details = _build_scan_details(
            matched,
            unmatched,
            current_user.skin_type,
        )

        safety_score = details[
            "safety_score"
        ]

        beneficial_count = sum(
            1
            for item in matched
            if item["ingredient"].safety_status
            == "Beneficial"
        )

        caution_count = (
            len(matched)
            - beneficial_count
        )

        scan = IngredientScan(
            user_id=current_user.id,
            image_url=saved_image_url,
            product_name=(
                product_name.strip()
                if product_name
                else None
            ),
            total_ingredients=len(tokens),
            beneficial_count=beneficial_count,
            caution_count=caution_count,
            safety_score=safety_score,
            details_json=json.dumps(
                details,
                ensure_ascii=False,
            ),
        )

        db.add(scan)
        db.commit()
        db.refresh(scan)

        return _build_response(scan)

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        logger.exception(
            "Ingredient scan failed for user %s",
            current_user.id,
        )

        # Delete newly saved image if DB/OCR/matching failed.
        if saved_path is not None:
            try:
                if saved_path.exists():
                    saved_path.unlink()
            except OSError:
                logger.warning(
                    "Could not remove failed scan image: %s",
                    saved_path,
                )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Ingredient scanning failed. "
                "Please try again."
            ),
        )


# ---------------------------------------------------------------------------
# Scan history
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[IngredientScanOut],
)
def get_scan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """Return the authenticated user's scan history."""
    scans = (
        db.query(IngredientScan)
        .filter(
            IngredientScan.user_id
            == current_user.id
        )
        .order_by(
            IngredientScan.created_at.desc()
        )
        .all()
    )

    return [
        _build_response(scan)
        for scan in scans
    ]


# ---------------------------------------------------------------------------
# Single scan
# ---------------------------------------------------------------------------

@router.get(
    "/{scan_id}",
    response_model=IngredientScanOut,
)
def get_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """Return one scan belonging to current user."""
    scan = (
        db.query(IngredientScan)
        .filter(
            IngredientScan.id == scan_id,
            IngredientScan.user_id
            == current_user.id,
        )
        .first()
    )

    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient scan not found.",
        )

    return _build_response(scan)