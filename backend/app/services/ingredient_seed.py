from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Ingredient
from app.services.ingredient_data import (
    CATEGORY_DEFAULTS,
    INGREDIENTS,
    get_catalog_stats,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def _normalize_name(value: Any) -> str:
    """
    Normalize an ingredient name for case-insensitive duplicate detection.
    """
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .casefold()
        .split()
    )


def _safe_json(value: Any) -> str:
    """
    Serialize catalog values safely for SQLite/SQLAlchemy JSON-text columns.
    """
    if value is None:
        value = []

    return json.dumps(
        value,
        ensure_ascii=False,
    )


# ============================================================================
# Convert catalog entry -> database row
# ============================================================================

def _build_ingredient_row(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Convert one bundled catalog definition into an Ingredient model payload.

    Category defaults provide the baseline safety/personalization metadata,
    while an entry-level `overrides` dictionary can customize those defaults.
    """
    if not isinstance(entry, dict):
        raise ValueError("Ingredient catalog entry must be a dictionary.")

    name = str(entry.get("name", "")).strip()

    if not name:
        raise ValueError("Ingredient name cannot be empty.")

    category = str(entry.get("category", "")).strip()

    if not category:
        raise ValueError(
            f"Ingredient '{name}' is missing a category."
        )

    if category not in CATEGORY_DEFAULTS:
        raise ValueError(
            f"Unknown ingredient category '{category}' "
            f"for ingredient '{name}'."
        )

    defaults = CATEGORY_DEFAULTS[category]

    if not isinstance(defaults, dict):
        raise ValueError(
            f"Category defaults for '{category}' must be a dictionary."
        )

    overrides = entry.get("overrides", {})

    if not isinstance(overrides, dict):
        logger.warning(
            "Ignoring invalid overrides for ingredient '%s'.",
            name,
        )
        overrides = {}

    def field(key: str, fallback: Any = None) -> Any:
        """
        Return an entry override when available, otherwise category default.
        """
        if key in overrides:
            return overrides[key]

        if key in defaults:
            return defaults[key]

        return fallback

    function = str(
        entry.get("function", "")
    ).strip()

    if not function:
        raise ValueError(
            f"Ingredient '{name}' is missing its function."
        )

    inci_name = entry.get("inci_name")

    if inci_name is not None:
        inci_name = str(inci_name).strip() or None

    aliases = entry.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = []

    uses = entry.get("uses", [])
    if not isinstance(uses, list):
        uses = []

    suitable_skin_types = field(
        "suitable_skin_types",
        [],
    )

    if not isinstance(suitable_skin_types, list):
        suitable_skin_types = []

    avoid_skin_types = field(
        "avoid_skin_types",
        [],
    )

    if not isinstance(avoid_skin_types, list):
        avoid_skin_types = []

    try:
        safety_score = int(
            field("safety_score", 0)
        )
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid safety_score for ingredient '{name}'."
        )

    # Keep the catalog's score inside the expected 0–100 range.
    safety_score = max(
        0,
        min(100, safety_score),
    )

    safety_status = str(
        field("safety_status", "Unknown")
    ).strip()

    when_to_use = field(
        "when_to_use",
        None,
    )

    if when_to_use is not None:
        when_to_use = str(when_to_use).strip() or None

    precautions = field(
        "precautions",
        None,
    )

    if precautions is not None:
        precautions = str(precautions).strip() or None

    return {
        "name": name,
        "inci_name": inci_name,
        "aliases_json": _safe_json(aliases),
        "category": category,
        "function": function,
        "uses_json": _safe_json(uses),
        "safety_status": safety_status,
        "safety_score": safety_score,
        "suitable_skin_types_json": _safe_json(
            suitable_skin_types
        ),
        "avoid_skin_types_json": _safe_json(
            avoid_skin_types
        ),
        "when_to_use": when_to_use,
        "precautions": precautions,
    }


# ============================================================================
# Seed database
# ============================================================================

def seed_ingredients(db: Session) -> int:
    """
    Idempotently seed the bundled ingredient catalog.

    Existing database records are NOT overwritten.

    Returns:
        Number of newly inserted ingredients.
    """
    if db is None:
        raise ValueError("A valid SQLAlchemy Session is required.")

    stats = get_catalog_stats()

    total_ingredients = int(
        stats.get("total_ingredients", 0)
    )

    logger.info(
        "Bundled ingredient catalog contains %s ingredients.",
        total_ingredients,
    )

    if not stats.get("meets_1000_requirement", False):
        logger.warning(
            "Bundled ingredient catalog currently contains fewer "
            "than 1000 ingredients. Do not claim full SRS 1000+ "
            "ingredient database compliance until a verified bulk "
            "dataset is loaded."
        )

    try:
        # ------------------------------------------------------------------
        # Load existing names once.
        # ------------------------------------------------------------------
        existing_names = {
            _normalize_name(name)
            for (name,) in db.query(
                Ingredient.name
            ).all()
            if name
        }

        rows_to_insert: list[Ingredient] = []

        # ------------------------------------------------------------------
        # Build new database rows.
        # ------------------------------------------------------------------
        for entry in INGREDIENTS:
            if not isinstance(entry, dict):
                logger.warning(
                    "Skipping invalid ingredient catalog entry: %r",
                    entry,
                )
                continue

            name = str(
                entry.get("name", "")
            ).strip()

            normalized_name = _normalize_name(name)

            if not normalized_name:
                logger.warning(
                    "Skipping catalog entry with empty ingredient name."
                )
                continue

            # Already present in database.
            if normalized_name in existing_names:
                continue

            try:
                row = _build_ingredient_row(entry)
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping invalid ingredient '%s': %s",
                    name,
                    exc,
                )
                continue

            rows_to_insert.append(
                Ingredient(**row)
            )

            # Prevent duplicate entries inside INGREDIENTS itself.
            existing_names.add(normalized_name)

        # ------------------------------------------------------------------
        # Nothing new to insert.
        # ------------------------------------------------------------------
        if not rows_to_insert:
            logger.info(
                "Ingredient database is already seeded; "
                "no new ingredients were inserted."
            )
            return 0

        # ------------------------------------------------------------------
        # Persist in one transaction.
        # ------------------------------------------------------------------
        db.add_all(rows_to_insert)
        db.commit()

        inserted = len(rows_to_insert)

        logger.info(
            "Seeded %s new skincare ingredients.",
            inserted,
        )

        return inserted

    except SQLAlchemyError:
        # SQLAlchemy requires the Session to be explicitly rolled back after
        # a failed flush/commit before it can safely be reused.
        db.rollback()

        logger.exception(
            "Failed to seed skincare ingredients."
        )

        raise

    except Exception:
        # Also rollback unexpected application-level failures so the caller
        # never receives a Session left inside a failed transaction.
        db.rollback()

        logger.exception(
            "Unexpected error while seeding skincare ingredients."
        )

        raise


# ============================================================================
# Diagnostics
# ============================================================================

def get_ingredient_count(db: Session) -> int:
    """
    Return the current number of ingredient records in the database.
    """
    if db is None:
        raise ValueError("A valid SQLAlchemy Session is required.")

    return db.query(Ingredient).count()