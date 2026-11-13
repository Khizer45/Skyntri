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
from app.db.models import (
    Appointment,
    AuditEvent,
    ContactMessage,
    DoctorProfile,
    Order,
    Product,
    SkinAnalysis,
    User,
)
from app.dependencies import require_admin
from app.services import app_settings, audit, connections, disease_screening, llm
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
        "clinic": {
            "doctors": db.query(func.count(DoctorProfile.id)).filter(DoctorProfile.status == "approved").scalar() or 0,
            "doctors_pending": db.query(func.count(DoctorProfile.id))
            .filter(DoctorProfile.status == "pending").scalar() or 0,
            "appointments_upcoming": db.query(func.count(Appointment.id))
            .filter(Appointment.status.in_(["requested", "confirmed"]), Appointment.starts_at >= now).scalar() or 0,
            "appointments_7d": db.query(func.count(Appointment.id))
            .filter(Appointment.created_at >= week_ago).scalar() or 0,
        },
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
            raise HTTPException(
                status_code=400,
                detail="Role must be 'user' or 'admin'. Doctors are approved under Admin -> Doctors.",
            )
        if payload.role != user.role:
            audit.record(db, admin.id, "user.role_changed", user.id, f"{user.role} -> {payload.role}")
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


# ============================================================
# Settings (run-time switches) and audit trail
# ============================================================

class SettingUpdate(BaseModel):
    key: str
    value: bool


def _settings_payload(db: Session) -> dict:
    return {
        "settings": app_settings.describe(db),
        # Whether each optional service has its key. Only yes/no is reported,
        # never a key. "Set" is not "working": that is what the test below is for.
        "integrations": {
            "google_sign_in": bool(settings.google_client_id),
            "card_payments": settings.stripe_configured,
            "paypal": settings.paypal_configured,
            "email": settings.smtp_configured,
            "assistant_llm": llm.text_available(),
            "assistant_images": llm.image_provider() is not None,
            "agent_scheduler": bool(settings.agents_scheduler_enabled),
        },
        "testable": sorted(connections.TESTS),
        "disease_model_installed": disease_screening.model_files_present(),
    }


@router.get("/settings")
def admin_get_settings(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _settings_payload(db)


@router.put("/settings")
def admin_update_setting(
    payload: SettingUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.key not in app_settings.EDITABLE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown setting.")

    if (
        payload.key == "disease_screening_enabled"
        and payload.value
        and not disease_screening.model_files_present()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The skin disease model files are not installed in backend/models/ yet.",
        )

    app_settings.set_value(db, payload.key, payload.value, updated_by=admin.id)
    audit.record(db, admin.id, "setting.changed", payload.key, str(payload.value).lower())
    db.commit()
    return _settings_payload(db)


@router.post("/connections/{name}/test")
def admin_test_connection(name: str, _admin: User = Depends(require_admin)):
    """
    Send one harmless request to an outside service with the configured key
    and report what it answered. Nothing is charged, created or e-mailed.
    """
    if name not in connections.TESTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown connection.")
    return connections.run(name)


@router.get("/audit")
def admin_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    events = db.query(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit).all()
    actor_ids = {e.actor for e in events}
    names = dict(db.query(User.id, User.email).filter(User.id.in_(actor_ids)).all()) if actor_ids else {}
    return [
        {
            "id": e.id,
            "actor": names.get(e.actor, e.actor),
            "action": e.action,
            "target": e.target,
            "detail": e.detail,
            "created_at": e.created_at,
        }
        for e in events
    ]
