"""
Administrator panel API: dashboard statistics and user management.
Product and order management live in routers/shop.py (/admin/products, /admin/orders).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import ContactMessage, Order, Product, SkinAnalysis, User
from app.dependencies import require_admin
from app.services import shop as shop_service

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    orders: int
    analyses: int


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.get("/stats")
def admin_stats(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    orders_by_status = dict(db.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    payments = dict(
        db.query(Order.payment_status, func.coalesce(func.sum(Order.subtotal), 0.0))
        .filter(Order.status != "cancelled")
        .group_by(Order.payment_status)
        .all()
    )

    products = db.query(Product).all()
    recent = db.query(Order).order_by(desc(Order.created_at)).limit(5).all()

    return {
        "currency": settings.shop_currency,
        "users": {
            "total": db.query(func.count(User.id)).scalar() or 0,
            "admins": db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0,
            "new_7d": db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0,
        },
        "products": {
            "total": len(products),
            "active": sum(1 for p in products if p.is_active),
            "out_of_stock": sum(1 for p in products if p.is_active and p.stock <= 0),
            "low_stock": sum(1 for p in products if p.is_active and 0 < p.stock <= 5),
            "stale_prices": sum(1 for p in products if p.is_active and shop_service.price_is_stale(p)),
        },
        "orders": {
            "total": sum(orders_by_status.values()),
            "by_status": {s: int(orders_by_status.get(s, 0)) for s in
                          ["pending", "confirmed", "shipped", "delivered", "cancelled"]},
        },
        "payments": {
            "collected": round(float(payments.get("paid", 0.0)), 2),
            "outstanding": round(float(payments.get("unpaid", 0.0)), 2),
            "refunded": round(float(payments.get("refunded", 0.0)), 2),
        },
        "analyses": {
            "total": db.query(func.count(SkinAnalysis.id)).scalar() or 0,
            "last_7d": db.query(func.count(SkinAnalysis.id)).filter(SkinAnalysis.created_at >= week_ago).scalar() or 0,
        },
        "contact_messages": db.query(func.count(ContactMessage.id)).scalar() or 0,
        "recent_orders": [
            {
                "id": o.id,
                "status": o.status,
                "payment_status": o.payment_status,
                "subtotal": round(o.subtotal, 2),
                "currency": o.currency,
                "shipping_name": o.shipping_name,
                "created_at": o.created_at,
            }
            for o in recent
        ],
    }


@router.get("/users", response_model=list[AdminUserOut])
def admin_users(
    q: str | None = Query(default=None, max_length=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))

    users = query.order_by(desc(User.created_at)).limit(500).all()
    order_counts = dict(db.query(Order.user_id, func.count(Order.id)).group_by(Order.user_id).all())
    analysis_counts = dict(
        db.query(SkinAnalysis.user_id, func.count(SkinAnalysis.id)).group_by(SkinAnalysis.user_id).all()
    )

    return [
        AdminUserOut(
            id=u.id, full_name=u.full_name, email=u.email, role=u.role or "user",
            is_active=u.is_active, created_at=u.created_at,
            orders=int(order_counts.get(u.id, 0)), analyses=int(analysis_counts.get(u.id, 0)),
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.id == admin.id and (payload.role == "user" or payload.is_active is False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin access or deactivate yourself.",
        )

    if payload.role is not None:
        if payload.role not in {"user", "admin"}:
            raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'.")
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return AdminUserOut(
        id=user.id, full_name=user.full_name, email=user.email, role=user.role, is_active=user.is_active,
        created_at=user.created_at,
        orders=db.query(func.count(Order.id)).filter(Order.user_id == user.id).scalar() or 0,
        analyses=db.query(func.count(SkinAnalysis.id)).filter(SkinAnalysis.user_id == user.id).scalar() or 0,
    )
