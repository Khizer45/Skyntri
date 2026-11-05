from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PRODUCT_CATEGORIES = [
    "Cleanser",
    "Moisturizer",
    "Sunscreen",
    "Serum",
    "Toner",
    "Exfoliant",
    "Spot treatment",
    "Mask",
    "Eye care",
    "Lip care",
    "Body care",
    "Other",
]

SKIN_TYPES = ["Normal", "Oily", "Dry", "Combination", "Sensitive"]

ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
PAYMENT_STATUSES = ["unpaid", "paid", "refunded"]


def _clean_list(values: list[str] | None, max_items: int = 100, max_len: int = 120) -> list[str]:
    seen: dict[str, str] = {}
    for value in values or []:
        text = " ".join(str(value).split())[:max_len]
        if text and text.lower() not in seen:
            seen[text.lower()] = text
        if len(seen) >= max_items:
            break
    return list(seen.values())


# ============================================================
# Products
# ============================================================

class ProductIn(BaseModel):
    """Admin create/update payload. Prices are entered by the admin; nothing is invented."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=4000)
    size: str | None = Field(default=None, max_length=60)

    # Full ingredient list (INCI), as a list or a comma-separated string.
    ingredients: list[str] | str = Field(default_factory=list)
    skin_types: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)

    price: float = Field(gt=0, le=10_000_000)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    price_source: str | None = Field(default=None, max_length=300)
    price_checked_at: datetime | None = None

    stock: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = True
    is_sponsored: bool = False

    @field_validator("ingredients", mode="before")
    @classmethod
    def _split_ingredients(cls, value):
        if isinstance(value, str):
            value = [part for chunk in value.split("\n") for part in chunk.split(",")]
        return _clean_list(value)

    @field_validator("skin_types", "concerns", mode="before")
    @classmethod
    def _clean(cls, value):
        if isinstance(value, str):
            value = value.split(",")
        return _clean_list(value, max_items=20, max_len=60)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class ProductOut(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    description: str | None
    size: str | None
    ingredients: list[str]
    skin_types: list[str]
    concerns: list[str]
    price: float
    currency: str
    price_source: str | None
    price_checked_at: datetime | None
    price_is_stale: bool
    stock: int
    in_stock: bool
    image_url: str | None
    is_active: bool
    is_sponsored: bool
    cautions: list[str]
    created_at: datetime
    updated_at: datetime

    # Search-only fields
    matched_ingredients: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    match_score: float | None = None
    why: list[str] = Field(default_factory=list)


class ProductSearchOut(BaseModel):
    total: int
    items: list[ProductOut]
    ranking: str
    disclaimer: str


class RecommendationOut(BaseModel):
    based_on: list[str]
    ingredients: list[str]
    message: str
    items: list[ProductOut]


# ============================================================
# Cart
# ============================================================

class CartAdd(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=100)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class CartItemOut(BaseModel):
    id: str
    product: ProductOut
    quantity: int
    line_total: float
    available: bool
    problem: str | None = None


class CartOut(BaseModel):
    items: list[CartItemOut]
    item_count: int
    subtotal: float
    currency: str
    can_checkout: bool


# ============================================================
# Orders
# ============================================================

class CheckoutIn(BaseModel):
    shipping_name: str = Field(min_length=2, max_length=120)
    shipping_phone: str = Field(min_length=7, max_length=20, pattern=r"^[0-9+\-() ]+$")
    shipping_address: str = Field(min_length=5, max_length=500)
    shipping_city: str = Field(min_length=2, max_length=80)
    notes: str | None = Field(default=None, max_length=500)


class OrderItemOut(BaseModel):
    id: str
    product_id: str | None
    product_name: str
    brand: str
    unit_price: float
    quantity: int
    line_total: float


class OrderOut(BaseModel):
    id: str
    user_id: str
    user_email: str | None = None
    status: str
    payment_method: str
    payment_status: str = "unpaid"
    subtotal: float
    currency: str
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled"] | None = None
    payment_status: Literal["unpaid", "paid", "refunded"] | None = None
