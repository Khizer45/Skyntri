"""
Shop helpers: ingredient-based product matching, serialization, safety notes.

Ranking is transparent (SEC-PROD-005): ingredient match share first, then
price. Sponsored products are never boosted; they are only labelled.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Ingredient, Product
from app.schemas_shop import ProductOut
from app.services.uploads import signed_url

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

FRAGRANCE_KEYS = {"fragrance", "parfum", "perfume", "aroma"}
DRYING_ALCOHOL_KEYS = {"alcoholdenat", "sdalcohol", "denaturedalcohol", "ethanol"}

SHOP_DISCLAIMER = (
    "Product information and prices are entered by the Skyntri team from the listed "
    "source; check the price and ingredients with the seller. Products can still cause "
    "reactions: patch test new products. Cosmetic products do not treat skin diseases."
)

# Ingredients from Model A recommendations that should not be suggested for
# self-purchase through the shop (prescription-only in some markets).
NOT_FOR_SHOP_RECOMMENDATION = {"adapalene", "tretinoin", "hydroquinone"}


def key(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = re.sub(r"\(.*?\)", " ", text)  # drop bracketed notes: "Niacinamide (Vitamin B3)"
    return _NON_ALNUM.sub("", text)


def json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return []
    return [str(v) for v in decoded] if isinstance(decoded, list) else []


# Built-in synonyms that must work even if the ingredient database lacks them.
BUILTIN_ALIASES = {
    "parfum": "fragrance",
    "perfume": "fragrance",
    "aroma": "fragrance",
    "fragranceparfum": "fragrance",
    "parfumfragrance": "fragrance",
    "water": "aqua",
    "aquawater": "aqua",
    "wateraqua": "aqua",
    "vitaminb3": "niacinamide",
    "nicotinamide": "niacinamide",
}


def alias_map(db: Session) -> dict[str, str]:
    """comparison key -> canonical key, from the curated ingredient database."""
    mapping: dict[str, str] = dict(BUILTIN_ALIASES)
    for ingredient in db.query(Ingredient).all():
        canonical = key(ingredient.name)
        if not canonical:
            continue
        for name in [ingredient.name, ingredient.inci_name, *json_list(ingredient.aliases_json)]:
            k = key(name)
            if k and k not in mapping:
                mapping[k] = canonical
    return mapping


def canonical_keys(names: list[str], aliases: dict[str, str]) -> list[str]:
    out: list[str] = []
    for name in names:
        k = key(name)
        if not k:
            continue
        canonical = aliases.get(k, k)
        if canonical not in out:
            out.append(canonical)
    return out


def _matches(wanted: str, product_keys: list[str]) -> bool:
    for pk in product_keys:
        if wanted == pk:
            return True
        if len(wanted) >= 5 and (wanted in pk or pk in wanted) and min(len(pk), len(wanted)) >= 5:
            return True
        if len(wanted) >= 6 and fuzz.ratio(wanted, pk) >= 92:
            return True
    return False


def match_product(
    product: Product,
    wanted: list[tuple[str, str]],
) -> tuple[list[str], list[str]]:
    """wanted = [(display name, canonical key)] -> (matched names, missing names)."""
    product_keys = json_list(product.ingredient_keys_json)
    matched, missing = [], []
    for display, k in wanted:
        (matched if _matches(k, product_keys) else missing).append(display)
    return matched, missing


def contains_any(product: Product, keys: list[str]) -> list[str]:
    product_keys = json_list(product.ingredient_keys_json)
    return [k for k in keys if _matches(k, product_keys)]


def cautions_for(product: Product) -> list[str]:
    product_keys = set(json_list(product.ingredient_keys_json))
    notes = []
    if any(any(f in pk for f in FRAGRANCE_KEYS) for pk in product_keys):
        notes.append("Contains fragrance; may irritate sensitive skin.")
    if product_keys & DRYING_ALCOHOL_KEYS:
        notes.append("Contains drying alcohol.")
    notes.append("Patch test before first use.")
    return notes


def price_is_stale(product: Product) -> bool:
    checked = product.price_checked_at
    if checked is None:
        return True
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - checked > timedelta(days=settings.price_stale_after_days)


def product_image_url(value: str | None) -> str | None:
    return signed_url(value)


def serialize(
    product: Product,
    matched: list[str] | None = None,
    missing: list[str] | None = None,
    why: list[str] | None = None,
) -> ProductOut:
    total = len(matched or []) + len(missing or [])
    return ProductOut(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        description=product.description,
        size=product.size,
        ingredients=json_list(product.ingredients_json),
        skin_types=json_list(product.skin_types_json),
        concerns=json_list(product.concerns_json),
        price=round(float(product.price), 2),
        currency=product.currency,
        price_source=product.price_source,
        price_checked_at=product.price_checked_at,
        price_is_stale=price_is_stale(product),
        stock=product.stock,
        in_stock=product.stock > 0,
        image_url=product_image_url(product.image_url),
        is_active=product.is_active,
        is_sponsored=product.is_sponsored,
        cautions=cautions_for(product),
        created_at=product.created_at,
        updated_at=product.updated_at,
        matched_ingredients=matched or [],
        missing_ingredients=missing or [],
        match_score=round(len(matched or []) / total, 3) if total else None,
        why=why or [],
    )


def apply_payload(product: Product, payload, db: Session) -> None:
    """Copy an admin ProductIn payload onto a Product row."""
    aliases = alias_map(db)
    product.name = payload.name.strip()
    product.brand = payload.brand.strip()
    product.category = payload.category.strip()
    product.description = payload.description
    product.size = payload.size
    product.ingredients_json = json.dumps(payload.ingredients)
    product.ingredient_keys_json = json.dumps(canonical_keys(payload.ingredients, aliases))
    product.skin_types_json = json.dumps(payload.skin_types)
    product.concerns_json = json.dumps(payload.concerns)
    product.price = round(float(payload.price), 2)
    product.currency = payload.currency
    product.price_source = payload.price_source
    product.price_checked_at = payload.price_checked_at
    product.stock = payload.stock
    product.is_active = payload.is_active
    product.is_sponsored = payload.is_sponsored
