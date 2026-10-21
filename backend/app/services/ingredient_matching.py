from __future__ import annotations

import json
import re
import unicodedata

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.db.models import Ingredient


# ---------------------------------------------------------------------------
# Matching configuration
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 82
MIN_TOKEN_LENGTH = 2
MIN_FUZZY_LENGTH = 4

_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _safe_json_list(value: str | None) -> list:
    """Safely decode a JSON list stored in the database."""
    if not value:
        return []

    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return []

    return decoded if isinstance(decoded, list) else []


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_ingredient_name(value: str | None) -> str:
    """
    Normalize an ingredient name for reliable matching.

    Examples:
        Sodium  Hyaluronate -> sodium hyaluronate
        L-Ascorbic Acid     -> l-ascorbic acid
        Niacinamide         -> niacinamide
    """
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.casefold().strip()

    normalized = normalized.replace("–", "-")
    normalized = normalized.replace("—", "-")
    normalized = normalized.replace("_", " ")

    normalized = _SPACE_RE.sub(" ", normalized)

    return normalized.strip()


def _comparison_key(value: str | None) -> str:
    """
    Create an aggressive comparison key.

    Hyphens, punctuation and whitespace are ignored.
    """
    normalized = normalize_ingredient_name(value)

    if not normalized:
        return ""

    return _NON_ALNUM_RE.sub("", normalized)


# ---------------------------------------------------------------------------
# OCR token cleanup
# ---------------------------------------------------------------------------

def _clean_token(token: str | None) -> str:
    """Clean an OCR/manual ingredient token."""
    if not token:
        return ""

    value = unicodedata.normalize("NFKC", str(token))

    value = value.strip(" \t\r\n,;:|•")

    value = _SPACE_RE.sub(" ", value)

    return value.strip()


def _is_valid_token(token: str) -> bool:
    """Reject obvious OCR noise."""
    if len(token) < MIN_TOKEN_LENGTH:
        return False

    if not re.search(r"[A-Za-z]", token):
        return False

    return True


# ---------------------------------------------------------------------------
# Database lookup
# ---------------------------------------------------------------------------

def _build_lookup(db: Session) -> dict[str, Ingredient]:
    """
    Build searchable lookup using:

    - primary ingredient name
    - INCI name
    - aliases
    """
    lookup: dict[str, Ingredient] = {}

    ingredients = db.query(Ingredient).all()

    for ingredient in ingredients:
        names: list[str] = []

        if ingredient.name:
            names.append(ingredient.name)

        if ingredient.inci_name:
            names.append(ingredient.inci_name)

        names.extend(
            str(alias)
            for alias in _safe_json_list(ingredient.aliases_json)
            if alias
        )

        for raw_name in names:
            normalized = normalize_ingredient_name(raw_name)

            if normalized:
                lookup[normalized] = ingredient

    return lookup


def _build_comparison_lookup(
    lookup: dict[str, Ingredient],
) -> dict[str, Ingredient]:
    """Build punctuation/spacing-insensitive lookup."""
    result: dict[str, Ingredient] = {}

    for searchable_name, ingredient in lookup.items():
        key = _comparison_key(searchable_name)

        if key:
            result[key] = ingredient

    return result


# ---------------------------------------------------------------------------
# Ingredient matching
# ---------------------------------------------------------------------------

def match_ingredients(
    tokens: list[str],
    db: Session,
) -> dict:
    """
    Match OCR/manual tokens against the ingredient database.

    Matching order:

    1. Exact normalized match
    2. Punctuation/spacing-insensitive match
    3. RapidFuzz WRatio fuzzy match

    Fuzzy matching is disabled for very short tokens to reduce
    false-positive ingredient matches.

    Returns:

        {
            "matched": [
                {
                    "token": "...",
                    "ingredient": Ingredient,
                    "score": 100.0
                }
            ],
            "unmatched": ["..."]
        }
    """
    lookup = _build_lookup(db)
    comparison_lookup = _build_comparison_lookup(lookup)

    cleaned_tokens = [
        _clean_token(token)
        for token in tokens
    ]

    valid_tokens = [
        token
        for token in cleaned_tokens
        if _is_valid_token(token)
    ]

    if not lookup:
        return {
            "matched": [],
            "unmatched": valid_tokens,
        }

    choices = list(lookup.keys())

    matched: list[dict] = []
    unmatched: list[str] = []

    seen_ingredient_ids: set[str] = set()

    for token in valid_tokens:
        normalized = normalize_ingredient_name(token)

        if not normalized:
            continue

        # ---------------------------------------------------------------
        # 1. Exact normalized match
        # ---------------------------------------------------------------
        ingredient = lookup.get(normalized)

        if ingredient is not None:
            score = 100.0

        else:
            # -----------------------------------------------------------
            # 2. Punctuation/spacing-insensitive match
            # -----------------------------------------------------------
            comparison_key = _comparison_key(token)

            ingredient = comparison_lookup.get(comparison_key)

            if ingredient is not None:
                score = 99.0

            else:
                # -------------------------------------------------------
                # 3. Fuzzy match
                #
                # Do not fuzzy-match very short OCR tokens.
                # Exact/comparison matching above still handles short
                # legitimate names such as AHA/BHA when present.
                # -------------------------------------------------------
                if len(comparison_key) < MIN_FUZZY_LENGTH:
                    unmatched.append(token)
                    continue

                result = process.extractOne(
                    normalized,
                    choices,
                    scorer=fuzz.WRatio,
                )

                if result is None:
                    unmatched.append(token)
                    continue

                best_match, fuzzy_score, _ = result
                fuzzy_score = float(fuzzy_score)

                if fuzzy_score < MATCH_THRESHOLD:
                    unmatched.append(token)
                    continue

                ingredient = lookup[best_match]
                score = fuzzy_score

        ingredient_id = str(ingredient.id)

        # Prevent duplicate ingredient records.
        if ingredient_id in seen_ingredient_ids:
            continue

        seen_ingredient_ids.add(ingredient_id)

        matched.append(
            {
                "token": token,
                "ingredient": ingredient,
                "score": round(score, 2),
            }
        )

    return {
        "matched": matched,
        "unmatched": unmatched,
    }


# ---------------------------------------------------------------------------
# Personalization
# ---------------------------------------------------------------------------

def personalize_for_skin_type(
    ingredient: Ingredient,
    user_skin_type: str | None,
) -> str | None:
    """
    Generate a skin-type-specific warning.

    This does not modify the database safety status.
    """
    if not user_skin_type:
        return None

    skin_type = user_skin_type.strip()

    if not skin_type:
        return None

    if skin_type.casefold() == "not set":
        return None

    avoid_types = _safe_json_list(
        ingredient.avoid_skin_types_json
    )

    normalized_avoid = {
        str(value).casefold().strip()
        for value in avoid_types
        if value
    }

    if skin_type.casefold() in normalized_avoid:
        precaution = (
            ingredient.precautions
            or "consider patch testing first."
        )

        return (
            f"May not be ideal for {skin_type.lower()} skin — "
            f"{precaution}"
        )

    return None


def get_ingredient_warning(
    ingredient: Ingredient,
    user_skin_type: str | None = None,
) -> str | None:
    """Return an additional personalized ingredient warning."""
    return personalize_for_skin_type(
        ingredient,
        user_skin_type,
    )