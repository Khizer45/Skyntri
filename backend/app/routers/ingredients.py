from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Ingredient


router = APIRouter(
    prefix="/ingredients",
    tags=["ingredients"],
)


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _safe_json_list(
    value: str | None,
) -> list:
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
# Serialization
# ---------------------------------------------------------------------------

def _serialize_ingredient(
    ingredient: Ingredient,
) -> dict:
    """Convert Ingredient ORM object into API response."""
    return {
        "id": ingredient.id,
        "name": ingredient.name,
        "inci_name": ingredient.inci_name,
        "aliases": _safe_json_list(
            ingredient.aliases_json
        ),
        "category": ingredient.category,
        "function": ingredient.function,
        "uses": _safe_json_list(
            ingredient.uses_json
        ),
        "safety_status": ingredient.safety_status,
        "safety_score": ingredient.safety_score,
        "suitable_skin_types": _safe_json_list(
            ingredient.suitable_skin_types_json
        ),
        "avoid_skin_types": _safe_json_list(
            ingredient.avoid_skin_types_json
        ),
        "when_to_use": ingredient.when_to_use,
        "precautions": ingredient.precautions,
        "created_at": ingredient.created_at,
    }


# ---------------------------------------------------------------------------
# List/search ingredients
# ---------------------------------------------------------------------------

@router.get("")
def list_ingredients(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    category: str | None = Query(
        default=None,
        max_length=100,
    ),
    safety_status: str | None = Query(
        default=None,
        max_length=50,
    ),
    skin_type: str | None = Query(
        default=None,
        max_length=50,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    """
    Browse/search the ingredient database.

    This endpoint exposes only ingredient information.
    It does not expose user records.
    """
    query = db.query(Ingredient)

    # ---------------------------------------------------------------
    # Search
    # ---------------------------------------------------------------
    if search:
        search_value = search.strip()

        if search_value:
            search_pattern = (
                f"%{search_value}%"
            )

            query = query.filter(
                or_(
                    Ingredient.name.ilike(
                        search_pattern
                    ),
                    Ingredient.inci_name.ilike(
                        search_pattern
                    ),
                    Ingredient.aliases_json.ilike(
                        search_pattern
                    ),
                )
            )

    # ---------------------------------------------------------------
    # Category
    # ---------------------------------------------------------------
    if category:
        query = query.filter(
            Ingredient.category
            == category.strip()
        )

    # ---------------------------------------------------------------
    # Safety status
    # ---------------------------------------------------------------
    if safety_status:
        query = query.filter(
            Ingredient.safety_status
            == safety_status.strip()
        )

    # ---------------------------------------------------------------
    # Get records
    # ---------------------------------------------------------------
    ingredients = (
        query
        .order_by(
            Ingredient.name.asc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    # ---------------------------------------------------------------
    # Skin-type filtering
    # ---------------------------------------------------------------
    if skin_type:
        normalized_skin_type = (
            skin_type.strip().casefold()
        )

        ingredients = [
            ingredient
            for ingredient in ingredients
            if normalized_skin_type
            in {
                str(value).casefold()
                for value in _safe_json_list(
                    ingredient.suitable_skin_types_json
                )
            }
        ]

    return {
        "items": [
            _serialize_ingredient(
                ingredient
            )
            for ingredient in ingredients
        ],
        "count": len(ingredients),
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.get("/categories")
def ingredient_categories(
    db: Session = Depends(get_db),
):
    """Return all available ingredient categories."""
    categories = (
        db.query(Ingredient.category)
        .distinct()
        .order_by(
            Ingredient.category.asc()
        )
        .all()
    )

    return {
        "categories": [
            category
            for (category,) in categories
            if category
        ]
    }


# ---------------------------------------------------------------------------
# Find by name
# ---------------------------------------------------------------------------

@router.get("/name/{ingredient_name}")
def get_ingredient_by_name(
    ingredient_name: str,
    db: Session = Depends(get_db),
):
    """Find ingredient by name, INCI name or alias."""
    normalized_name = (
        ingredient_name.strip().casefold()
    )

    if not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient name cannot be empty.",
        )

    ingredients = (
        db.query(Ingredient)
        .all()
    )

    for ingredient in ingredients:
        # Primary name
        if (
            ingredient.name
            and ingredient.name.casefold()
            == normalized_name
        ):
            return _serialize_ingredient(
                ingredient
            )

        # INCI
        if (
            ingredient.inci_name
            and ingredient.inci_name.casefold()
            == normalized_name
        ):
            return _serialize_ingredient(
                ingredient
            )

        # Aliases
        aliases = _safe_json_list(
            ingredient.aliases_json
        )

        if any(
            str(alias).casefold()
            == normalized_name
            for alias in aliases
            if alias
        ):
            return _serialize_ingredient(
                ingredient
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Ingredient not found.",
    )


# ---------------------------------------------------------------------------
# Find by ID
# ---------------------------------------------------------------------------

@router.get("/{ingredient_id}")
def get_ingredient(
    ingredient_id: str,
    db: Session = Depends(get_db),
):
    """Return detailed information for one ingredient."""
    ingredient = (
        db.query(Ingredient)
        .filter(
            Ingredient.id == ingredient_id
        )
        .first()
    )

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found.",
        )

    return _serialize_ingredient(
        ingredient
    )