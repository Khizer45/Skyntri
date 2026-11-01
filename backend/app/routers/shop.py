"""
Shop: product catalogue with ingredient-based search, recommendations,
cart and orders (cash on delivery), plus administrator management.

Access:
    GET  /products, /products/{id}, /products/meta       public
    GET  /products/recommended                           user
    /cart/*, /orders/*                                    user (own data only)
    /admin/products/*, /admin/orders/*                    admin
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import desc, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import CartItem, Order, OrderItem, Product, SkinAnalysis, User
from app.dependencies import get_current_user, require_admin
from app.schemas_shop import (
    ORDER_STATUSES,
    PRODUCT_CATEGORIES,
    SKIN_TYPES,
    CartAdd,
    CartItemOut,
    CartOut,
    CartUpdate,
    CheckoutIn,
    OrderItemOut,
    OrderOut,
    OrderStatusUpdate,
    ProductIn,
    ProductOut,
    ProductSearchOut,
    RecommendationOut,
)
from app.services import rate_limit, shop
from app.services.skin_analysis import CONDITION_RECOMMENDATIONS, DISPLAY_NAMES
from app.services.uploads import delete_upload, save_upload

router = APIRouter(tags=["shop"])

RANKING_TEXT = (
    "Ranked by how many of your searched ingredients each product contains, then by "
    "price (lowest first). Sponsored products are labelled and are not ranked higher."
)


def _parse_csv(value: str | None, limit: int = 15) -> list[str]:
    if not value:
        return []
    items = [" ".join(v.split())[:80] for v in value.split(",")]
    return [v for v in dict.fromkeys(items) if v][:limit]


def _get_product(db: Session, product_id: str, active_only: bool = True) -> Product:
    product = db.get(Product, product_id)
    if product is None or (active_only and not product.is_active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


# ============================================================
# Catalogue (public)
# ============================================================

@router.get("/products/meta")
def product_meta():
    return {
        "categories": PRODUCT_CATEGORIES,
        "skin_types": SKIN_TYPES,
        "currency": settings.shop_currency,
        "disclaimer": shop.SHOP_DISCLAIMER,
    }


@router.get("/products", response_model=ProductSearchOut)
def search_products(
    q: str | None = Query(default=None, max_length=100, description="Name or brand"),
    ingredients: str | None = Query(default=None, max_length=1000, description="Comma-separated wanted ingredients"),
    avoid: str | None = Query(default=None, max_length=1000, description="Comma-separated ingredients to exclude"),
    match: str = Query(default="any", pattern="^(any|all)$"),
    category: str | None = Query(default=None, max_length=60),
    skin_type: str | None = Query(default=None, max_length=30),
    concern: str | None = Query(default=None, max_length=60),
    max_price: float | None = Query(default=None, gt=0),
    in_stock: bool = False,
    sort: str = Query(default="relevance", pattern="^(relevance|price_asc|price_desc|newest)$"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Search products by the ingredients they contain (e.g. "niacinamide,
    salicylic acid"), exclude ingredients you want to avoid (e.g.
    "fragrance"), and filter by category, skin type, concern and budget.
    """
    aliases = shop.alias_map(db)
    wanted_names = _parse_csv(ingredients)
    wanted = [(name, shop.canonical_keys([name], aliases)[0]) for name in wanted_names if shop.key(name)]
    avoid_keys = shop.canonical_keys(_parse_csv(avoid), aliases)

    query = db.query(Product).filter(Product.is_active.is_(True))
    if category:
        query = query.filter(Product.category == category)
    if max_price:
        query = query.filter(Product.price <= max_price)
    if in_stock:
        query = query.filter(Product.stock > 0)

    text = (q or "").strip().lower()
    results = []
    for product in query.all():
        if text and text not in product.name.lower() and text not in product.brand.lower():
            continue
        types = shop.json_list(product.skin_types_json)
        if skin_type and types and skin_type not in types and "All" not in types:
            continue
        if concern and concern.lower() not in [c.lower() for c in shop.json_list(product.concerns_json)]:
            continue
        if avoid_keys and shop.contains_any(product, avoid_keys):
            continue

        matched, missing = shop.match_product(product, wanted) if wanted else ([], [])
        if wanted and not matched:
            continue
        if wanted and match == "all" and missing:
            continue
        results.append((product, matched, missing))

    if sort == "price_asc":
        results.sort(key=lambda r: r[0].price)
    elif sort == "price_desc":
        results.sort(key=lambda r: -r[0].price)
    elif sort == "newest":
        results.sort(key=lambda r: r[0].created_at, reverse=True)
    else:
        results.sort(key=lambda r: (-len(r[1]), r[0].price))

    page = results[offset: offset + limit]
    return ProductSearchOut(
        total=len(results),
        items=[shop.serialize(p, m, miss) for p, m, miss in page],
        ranking=RANKING_TEXT,
        disclaimer=shop.SHOP_DISCLAIMER,
    )


@router.get("/products/recommended", response_model=RecommendationOut)
def recommended_products(
    limit: int = Query(default=8, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Products containing ingredients suggested for the user's latest FACIAL
    skin-concern analysis. Disease-screening results never lead to product
    suggestions (SEC-PROD-004).
    """
    latest = (
        db.query(SkinAnalysis)
        .filter(SkinAnalysis.user_id == current_user.id)
        .order_by(desc(SkinAnalysis.created_at))
        .first()
    )

    if latest is None:
        return RecommendationOut(
            based_on=[], ingredients=[], items=[],
            message="Run a facial skin analysis to get ingredient-based product suggestions.",
        )

    if (latest.analysis_track or "facial_concerns") != "facial_concerns":
        return RecommendationOut(
            based_on=[], ingredients=[], items=[],
            message=(
                "Your latest result was a disease-screening result. Please get professional "
                "medical advice first; cosmetic products do not treat skin diseases."
            ),
        )

    reverse_names = {v: k for k, v in DISPLAY_NAMES.items()}
    concerns = [
        reverse_names.get(c.strip(), c.strip())
        for c in (latest.predicted_condition or "").split(",")
        if c.strip()
    ]
    concerns = [c for c in concerns if c in CONDITION_RECOMMENDATIONS]

    ingredient_names: list[str] = []
    for concern in concerns:
        for name in CONDITION_RECOMMENDATIONS[concern].get("ingredients", []):
            if shop.key(name) not in shop.NOT_FOR_SHOP_RECOMMENDATION and name not in ingredient_names:
                ingredient_names.append(name)

    if not ingredient_names:
        return RecommendationOut(
            based_on=[DISPLAY_NAMES.get(c, c) for c in concerns], ingredients=[], items=[],
            message="No specific ingredient suggestions for your latest analysis. A gentle cleanser, "
                    "moisturiser and daily sunscreen suit most skin.",
        )

    aliases = shop.alias_map(db)
    wanted = [(n, shop.canonical_keys([n], aliases)[0]) for n in ingredient_names]
    sensitive = (current_user.skin_type or "").lower() == "sensitive"
    fragrance_keys = shop.canonical_keys(["fragrance", "parfum"], aliases)

    scored = []
    for product in db.query(Product).filter(Product.is_active.is_(True), Product.stock > 0).all():
        if sensitive and shop.contains_any(product, fragrance_keys):
            continue
        matched, missing = shop.match_product(product, wanted)
        if matched:
            why = [f"Contains {m.lower()}, often used for "
                   f"{', '.join(DISPLAY_NAMES.get(c, c).lower() for c in concerns if m in CONDITION_RECOMMENDATIONS[c].get('ingredients', []))}."
                   for m in matched]
            scored.append((product, matched, missing, why))

    scored.sort(key=lambda r: (-len(r[1]), r[0].price))
    return RecommendationOut(
        based_on=[DISPLAY_NAMES.get(c, c) for c in concerns],
        ingredients=ingredient_names,
        items=[shop.serialize(p, m, miss, why) for p, m, miss, why in scored[:limit]],
        message=(
            "Suggestions are based on ingredients commonly used for your latest AI-estimated "
            "facial concerns. They are not medical advice. Patch test new products."
        ),
    )


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    return shop.serialize(_get_product(db, product_id))


# ============================================================
# Cart (user)
# ============================================================

def _cart(db: Session, user: User) -> CartOut:
    items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user.id)
        .order_by(CartItem.created_at)
        .all()
    )
    out, subtotal, currencies, ok = [], 0.0, set(), True
    for item in items:
        product = item.product
        problem = None
        if product is None or not product.is_active:
            problem = "This product is no longer available."
        elif product.stock < item.quantity:
            problem = f"Only {product.stock} left in stock."
        available = problem is None
        ok = ok and available
        line = round(float(product.price) * item.quantity, 2) if product else 0.0
        if available:
            subtotal += line
            currencies.add(product.currency)
        if product is not None:
            out.append(CartItemOut(id=item.id, product=shop.serialize(product), quantity=item.quantity,
                                   line_total=line, available=available, problem=problem))
    if len(currencies) > 1:
        ok = False
    return CartOut(
        items=out,
        item_count=sum(i.quantity for i in out),
        subtotal=round(subtotal, 2),
        currency=next(iter(currencies), settings.shop_currency),
        can_checkout=ok and bool(out),
    )


@router.get("/cart", response_model=CartOut)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _cart(db, current_user)


@router.post("/cart/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(payload: CartAdd, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = _get_product(db, payload.product_id)
    item = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id, CartItem.product_id == product.id)
        .first()
    )
    quantity = (item.quantity if item else 0) + payload.quantity
    quantity = min(quantity, settings.max_cart_quantity)
    if product.stock < 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This product is out of stock.")
    quantity = min(quantity, product.stock)

    if item:
        item.quantity = quantity
    else:
        db.add(CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity))
    db.commit()
    return _cart(db, current_user)


def _own_item(db: Session, user: User, item_id: str) -> CartItem:
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")
    return item


@router.patch("/cart/items/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: str,
    payload: CartUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _own_item(db, current_user, item_id)
    item.quantity = min(payload.quantity, settings.max_cart_quantity)
    db.commit()
    return _cart(db, current_user)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
def remove_cart_item(item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_item(db, current_user, item_id))
    db.commit()
    return _cart(db, current_user)


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Orders (user)
# ============================================================

def _order_out(order: Order, include_email: bool = False, db: Session | None = None) -> OrderOut:
    email = None
    if include_email and db is not None:
        user = db.get(User, order.user_id)
        email = user.email if user else None
    return OrderOut(
        id=order.id, user_id=order.user_id, user_email=email, status=order.status,
        payment_method=order.payment_method, subtotal=round(order.subtotal, 2), currency=order.currency,
        shipping_name=order.shipping_name, shipping_phone=order.shipping_phone,
        shipping_address=order.shipping_address, shipping_city=order.shipping_city, notes=order.notes,
        created_at=order.created_at, updated_at=order.updated_at,
        items=[OrderItemOut(id=i.id, product_id=i.product_id, product_name=i.product_name, brand=i.brand,
                            unit_price=round(i.unit_price, 2), quantity=i.quantity, line_total=round(i.line_total, 2))
               for i in order.items],
    )


def _restock(db: Session, order: Order) -> None:
    for item in order.items:
        if item.product_id:
            db.execute(update(Product).where(Product.id == item.product_id).values(stock=Product.stock + item.quantity))


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: CheckoutIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create an order from the cart. Prices are taken from the database (never
    from the client) and stock is reserved atomically. Payment: cash on delivery.
    """
    rate_limit.enforce(db, "order", current_user.id, settings.order_per_hour,
                       message="Too many orders. Please try again later.")

    cart = _cart(db, current_user)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your cart is empty.")
    if not cart.can_checkout:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Some items in your cart are unavailable or out of stock. Please update your cart.",
        )

    order = Order(
        user_id=current_user.id,
        status="pending",
        payment_method="cash_on_delivery",
        subtotal=cart.subtotal,
        currency=cart.currency,
        shipping_name=payload.shipping_name.strip(),
        shipping_phone=payload.shipping_phone.strip(),
        shipping_address=payload.shipping_address.strip(),
        shipping_city=payload.shipping_city.strip(),
        notes=(payload.notes or "").strip() or None,
    )

    try:
        for line in cart.items:
            reserved = db.execute(
                update(Product)
                .where(Product.id == line.product.id, Product.stock >= line.quantity, Product.is_active.is_(True))
                .values(stock=Product.stock - line.quantity)
            )
            if reserved.rowcount != 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"'{line.product.name}' just went out of stock. Please update your cart.",
                )
            order.items.append(OrderItem(
                product_id=line.product.id, product_name=line.product.name, brand=line.product.brand,
                unit_price=line.product.price, quantity=line.quantity, line_total=line.line_total,
            ))

        db.add(order)
        db.query(CartItem).filter(CartItem.user_id == current_user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return _order_out(order)


@router.get("/orders", response_model=list[OrderOut])
def my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(desc(Order.created_at)).all()
    return [_order_out(o) for o in orders]


def _own_order(db: Session, user: User, order_id: str) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _order_out(_own_order(db, current_user, order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = _own_order(db, current_user, order_id)
    if order.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Only pending orders can be cancelled. Please contact support.")
    order.status = "cancelled"
    _restock(db, order)
    db.commit()
    db.refresh(order)
    return _order_out(order)


# ============================================================
# Administration
# ============================================================

@router.get("/admin/products", response_model=list[ProductOut])
def admin_list_products(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [shop.serialize(p) for p in db.query(Product).order_by(desc(Product.updated_at)).all()]


@router.post("/admin/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def admin_create_product(payload: ProductIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = Product()
    shop.apply_payload(product, payload, db)
    db.add(product)
    db.commit()
    db.refresh(product)
    return shop.serialize(product)


@router.put("/admin/products/{product_id}", response_model=ProductOut)
def admin_update_product(
    product_id: str,
    payload: ProductIn,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _get_product(db, product_id, active_only=False)
    shop.apply_payload(product, payload, db)
    product.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return shop.serialize(product)


@router.delete("/admin/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product(product_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Deletes the product. Past orders keep their snapshot (name, brand, price)."""
    product = _get_product(db, product_id, active_only=False)
    image = product.image_url
    db.query(CartItem).filter(CartItem.product_id == product.id).delete(synchronize_session=False)
    db.query(OrderItem).filter(OrderItem.product_id == product.id).update(
        {OrderItem.product_id: None}, synchronize_session=False
    )
    db.delete(product)
    db.commit()
    delete_upload(image)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/products/{product_id}/image", response_model=ProductOut)
def admin_upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _get_product(db, product_id, active_only=False)
    new_url = save_upload(file, "products")
    old_url = product.image_url
    product.image_url = new_url
    db.commit()
    db.refresh(product)
    if old_url and old_url != new_url:
        delete_upload(old_url)
    return shop.serialize(product)


ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


@router.get("/admin/orders", response_model=list[OrderOut])
def admin_list_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status_filter:
        if status_filter not in ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Unknown order status.")
        query = query.filter(Order.status == status_filter)
    return [_order_out(o, include_email=True, db=db) for o in query.order_by(desc(Order.created_at)).limit(500)]


@router.patch("/admin/orders/{order_id}", response_model=OrderOut)
def admin_update_order(
    order_id: str,
    payload: OrderStatusUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if payload.status != order.status:
        if payload.status not in ALLOWED_TRANSITIONS[order.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An order cannot move from '{order.status}' to '{payload.status}'.",
            )
        if payload.status == "cancelled":
            _restock(db, order)
        order.status = payload.status
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)
    return _order_out(order, include_email=True, db=db)
