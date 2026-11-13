"""
Automation.

/admin/automation/...   Administrators manage API keys, webhooks, agents
                        and clinic posts (session login required).
/automation/v1/...      For n8n, Zapier and custom agents. Authenticated
                        with an API key in the "X-API-Key" header (or
                        "Authorization: Bearer <key>"). Each key has scopes.
/posts                  Published clinic posts for signed-in users.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import AgentRun, ApiKey, Appointment, ClinicPost, User, WebhookDelivery, WebhookEndpoint
from app.dependencies import get_current_user, require_admin
from app.services import agents, audit, automation, clinic, rate_limit
from app.services.clinic import now_utc

router = APIRouter(tags=["automation"])


# ============================================================
# Schemas
# ============================================================

class ApiKeyIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    scopes: list[str] = Field(min_length=1, max_length=10)


class WebhookIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    url: str = Field(min_length=8, max_length=500)
    events: list[str] = Field(default_factory=lambda: ["*"], max_length=20)
    include_contact: bool = False
    is_active: bool = True


class PostIn(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=10, max_length=5000)
    kind: Literal["tip", "announcement"] = "tip"
    publish: bool = False


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    body: str | None = Field(default=None, min_length=10, max_length=5000)
    publish: bool | None = None


def _key_out(row: ApiKey) -> dict:
    return {
        "id": row.id, "name": row.name, "prefix": row.prefix, "scopes": sorted(automation.key_scopes(row)),
        "created_at": row.created_at, "last_used_at": row.last_used_at, "revoked": row.revoked_at is not None,
    }


def _webhook_out(row: WebhookEndpoint, with_secret: bool = False) -> dict:
    out = {
        "id": row.id, "name": row.name, "url": row.url,
        "events": [e for e in (row.events or "*").split(",") if e],
        "include_contact": row.include_contact, "is_active": row.is_active,
        "last_delivery_at": row.last_delivery_at, "last_status": row.last_status,
        "failure_count": row.failure_count, "created_at": row.created_at,
    }
    if with_secret:
        out["secret"] = automation.endpoint_secret(row.id)
    return out


def _post_out(row: ClinicPost) -> dict:
    return {
        "id": row.id, "title": row.title, "body": row.body, "kind": row.kind, "status": row.status,
        "source": row.source, "created_at": row.created_at, "published_at": row.published_at,
    }


def _run_out(row: AgentRun) -> dict:
    try:
        details = json.loads(row.details) if row.details else None
    except ValueError:
        details = None
    return {
        "id": row.id, "agent": row.agent, "label": agents.AGENTS.get(row.agent, (None, row.agent))[1],
        "status": row.status, "triggered_by": row.triggered_by, "summary": row.summary, "details": details,
        "started_at": row.started_at, "finished_at": row.finished_at,
    }


# ============================================================
# Admin: overview, API keys, webhooks
# ============================================================

@router.get("/admin/automation")
def automation_overview(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    keys = db.query(ApiKey).order_by(desc(ApiKey.created_at)).limit(100).all()
    hooks = db.query(WebhookEndpoint).order_by(desc(WebhookEndpoint.created_at)).limit(100).all()
    runs = db.query(AgentRun).order_by(desc(AgentRun.started_at)).limit(30).all()
    return {
        "scopes": automation.SCOPES,
        "events": automation.EVENTS,
        "agents": [{"name": name, "label": label} for name, (_fn, label) in agents.AGENTS.items()],
        "scheduler_enabled": bool(settings.agents_scheduler_enabled),
        "daily_hour": settings.agent_daily_hour,
        "timezone": settings.clinic_timezone,
        "api_keys": [_key_out(k) for k in keys],
        "webhooks": [_webhook_out(h) for h in hooks],
        "runs": [_run_out(r) for r in runs],
    }


@router.post("/admin/automation/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        row, plain = automation.create_api_key(db, payload.name, payload.scopes, admin.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    db.flush()
    audit.record(db, admin.id, "api_key.created", row.id, f"{row.name}: {row.scopes}")
    db.commit()
    db.refresh(row)
    # The only time the full key is returned.
    return {**_key_out(row), "key": plain}


@router.delete("/admin/automation/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(ApiKey, key_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found.")
    if row.revoked_at is None:
        row.revoked_at = now_utc()
        audit.record(db, admin.id, "api_key.revoked", row.id, row.name)
        db.commit()


def _clean_events(events: list[str]) -> str:
    events = [e.strip() for e in events if e.strip()] or ["*"]
    unknown = [e for e in events if e != "*" and e not in automation.EVENTS]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown event: {unknown[0]}")
    return "*" if "*" in events else ",".join(sorted(set(events)))


def _safe_url(url: str) -> str:
    try:
        return automation.validate_webhook_url(url)
    except automation.UnsafeWebhookUrl as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None


@router.post("/admin/automation/webhooks", status_code=status.HTTP_201_CREATED)
def create_webhook(payload: WebhookIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = WebhookEndpoint(
        name=payload.name.strip(), url=_safe_url(payload.url), events=_clean_events(payload.events),
        include_contact=payload.include_contact, is_active=payload.is_active, created_by=admin.id,
    )
    db.add(row)
    db.flush()
    audit.record(db, admin.id, "webhook.created", row.id, f"{row.name} contact={row.include_contact}")
    db.commit()
    db.refresh(row)
    return _webhook_out(row, with_secret=True)


def _webhook(db: Session, webhook_id: str) -> WebhookEndpoint:
    row = db.get(WebhookEndpoint, webhook_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook not found.")
    return row


@router.get("/admin/automation/webhooks/{webhook_id}")
def get_webhook(webhook_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = _webhook(db, webhook_id)
    deliveries = (
        db.query(WebhookDelivery).filter(WebhookDelivery.endpoint_id == row.id)
        .order_by(desc(WebhookDelivery.created_at)).limit(20).all()
    )
    return {
        **_webhook_out(row, with_secret=True),
        "deliveries": [
            {"id": d.id, "event": d.event, "ok": d.ok, "status_code": d.status_code, "error": d.error,
             "created_at": d.created_at}
            for d in deliveries
        ],
    }


@router.put("/admin/automation/webhooks/{webhook_id}")
def update_webhook(
    webhook_id: str, payload: WebhookIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    row = _webhook(db, webhook_id)
    row.name = payload.name.strip()
    row.url = _safe_url(payload.url)
    row.events = _clean_events(payload.events)
    row.include_contact = payload.include_contact
    if payload.is_active and not row.is_active:
        row.failure_count = 0
    row.is_active = payload.is_active
    audit.record(db, admin.id, "webhook.updated", row.id, f"{row.name} contact={row.include_contact}")
    db.commit()
    db.refresh(row)
    return _webhook_out(row, with_secret=True)


@router.delete("/admin/automation/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = _webhook(db, webhook_id)
    db.query(WebhookDelivery).filter(WebhookDelivery.endpoint_id == row.id).delete(synchronize_session=False)
    audit.record(db, admin.id, "webhook.deleted", row.id, row.name)
    db.delete(row)
    db.commit()


@router.post("/admin/automation/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Send a "test.ping" event to this endpoint now and report the result."""
    row = _webhook(db, webhook_id)
    envelope = {
        "id": "test", "event": "test.ping", "created_at": now_utc().isoformat(),
        "data": {"message": f"Hello from {settings.clinic_name}."},
    }
    delivery = WebhookDelivery(endpoint_id=row.id, event="test.ping", payload=json.dumps(envelope))
    db.add(delivery)
    db.commit()
    automation.deliver(db, [delivery.id])
    db.refresh(delivery)
    return {"ok": delivery.ok, "status_code": delivery.status_code, "error": delivery.error}


# ============================================================
# Admin: agents and posts
# ============================================================

def _run_or_404(db: Session, name: str, triggered_by: str) -> dict:
    if name not in agents.AGENTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown agent.")
    return _run_out(agents.run_agent(db, name, triggered_by))


@router.post("/admin/automation/agents/{name}/run")
def admin_run_agent(name: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _run_or_404(db, name, f"admin:{admin.id}")


@router.get("/admin/posts")
def admin_list_posts(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [_post_out(p) for p in db.query(ClinicPost).order_by(desc(ClinicPost.created_at)).limit(200).all()]


def _create_post(db: Session, payload: PostIn, source: str) -> ClinicPost:
    post = ClinicPost(
        title=payload.title.strip(), body=payload.body.strip(), kind=payload.kind, source=source,
        status="published" if payload.publish else "draft",
        published_at=now_utc() if payload.publish else None,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    if payload.publish:
        agents.emit_post_published(db, post)
    return post


@router.post("/admin/posts", status_code=status.HTTP_201_CREATED)
def admin_create_post(payload: PostIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _post_out(_create_post(db, payload, "admin"))


@router.patch("/admin/posts/{post_id}")
def admin_update_post(
    post_id: str, payload: PostUpdate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    post = db.get(ClinicPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found.")
    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.body is not None:
        post.body = payload.body.strip()

    newly_published = False
    if payload.publish is True and post.status != "published":
        post.status, post.published_at, newly_published = "published", now_utc(), True
    elif payload.publish is False:
        post.status, post.published_at = "draft", None
    db.commit()
    db.refresh(post)
    if newly_published:
        agents.emit_post_published(db, post)
    return _post_out(post)


@router.delete("/admin/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_post(post_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    post = db.get(ClinicPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found.")
    db.delete(post)
    db.commit()


@router.get("/posts")
def published_posts(
    limit: int = Query(default=5, ge=1, le=30),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ClinicPost).filter(ClinicPost.status == "published")
        .order_by(desc(ClinicPost.published_at)).limit(limit).all()
    )
    return [_post_out(p) for p in rows]


# ============================================================
# API for automation tools (API key)
# ============================================================

def api_key_with(scope: str):
    """Dependency: a valid, unrevoked API key that has `scope`."""

    def dependency(
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> ApiKey:
        plain = x_api_key or ""
        if not plain and authorization and authorization.lower().startswith("bearer "):
            plain = authorization[7:].strip()

        row = automation.find_api_key(db, plain)
        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid API key is required.")
        if scope not in automation.key_scopes(row):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This API key lacks the '{scope}' scope.")

        rate_limit.enforce(db, "api_key", row.id, settings.automation_requests_per_hour)
        row.last_used_at = now_utc()
        db.commit()
        return row

    return dependency


@router.get("/automation/v1/summary/daily")
def api_daily_summary(_key: ApiKey = Depends(api_key_with("read:summary")), db: Session = Depends(get_db)):
    """Yesterday's numbers (same content as the daily report), without running the agent."""
    last = (
        db.query(AgentRun).filter(AgentRun.agent == "daily_report", AgentRun.status == "ok")
        .order_by(desc(AgentRun.started_at)).first()
    )
    return _run_out(last) if last else {"summary": None, "details": None}


@router.get("/automation/v1/appointments")
def api_list_appointments(
    hours_ahead: int = Query(default=24, ge=1, le=24 * 60),
    status_filter: str = Query(default="confirmed", alias="status", pattern="^(requested|confirmed|all)$"),
    _key: ApiKey = Depends(api_key_with("read:appointments")),
    db: Session = Depends(get_db),
):
    """Upcoming appointments with contact details, e.g. for reminder workflows."""
    now = now_utc()
    query = db.query(Appointment).filter(
        Appointment.starts_at >= now, Appointment.starts_at <= now + timedelta(hours=hours_ahead)
    )
    if status_filter == "all":
        query = query.filter(Appointment.status.in_(clinic.ACTIVE_STATUSES))
    else:
        query = query.filter(Appointment.status == status_filter)

    items = []
    for appointment in query.order_by(asc(Appointment.starts_at)).limit(500).all():
        data, contact = clinic.event_data(appointment)
        items.append({**data, "contact": contact})
    return {"count": len(items), "appointments": items}


class ApiAppointmentUpdate(BaseModel):
    status: Literal["confirmed", "cancelled"]
    reason: str | None = Field(default=None, max_length=300)


@router.post("/automation/v1/appointments/{appointment_id}/status")
def api_update_appointment(
    appointment_id: str,
    payload: ApiAppointmentUpdate,
    key: ApiKey = Depends(api_key_with("write:appointments")),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")

    allowed = {"requested": {"confirmed", "cancelled"}, "confirmed": {"cancelled"}}
    if payload.status not in allowed.get(appointment.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"An appointment cannot go from '{appointment.status}' to '{payload.status}'."
        )
    if payload.status == "cancelled":
        appointment.status, appointment.slot_lock = "cancelled", None
        appointment.cancelled_by = "automation"
        appointment.cancel_reason = (payload.reason or "").strip() or None
        if appointment.payment_status == "paid":
            appointment.payment_status = "refund_due"
    else:
        appointment.status = "confirmed"

    audit.record(db, f"api_key:{key.id}", f"appointment.{payload.status}", appointment.id, key.name)
    db.commit()
    db.refresh(appointment)
    data, contact = clinic.event_data(appointment)
    automation.emit(db, "appointment.updated", data, contact)
    return data


@router.post("/automation/v1/posts", status_code=status.HTTP_201_CREATED)
def api_create_post(
    payload: PostIn, key: ApiKey = Depends(api_key_with("write:posts")), db: Session = Depends(get_db)
):
    post = _create_post(db, payload, "api")
    audit.record(db, f"api_key:{key.id}", "post.created", post.id, key.name)
    db.commit()
    return _post_out(post)


@router.post("/automation/v1/agents/{name}/run")
def api_run_agent(
    name: str,
    once_per: Literal["hour", "day"] | None = Query(
        default=None, description="Skip the run if it already happened in this hour / on this day."
    ),
    key: ApiKey = Depends(api_key_with("run:agents")),
    db: Session = Depends(get_db),
):
    if name not in agents.AGENTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown agent.")

    run_key = None
    if once_per:
        local = datetime.now(timezone.utc).astimezone(clinic.clinic_tz())
        run_key = f"{name}:{local:%Y-%m-%dT%H}" if once_per == "hour" else f"{name}:{local:%Y-%m-%d}"

    run = agents.run_agent(db, name, f"api_key:{key.id}", run_key)
    if run is None:
        return {"skipped": True, "reason": f"Already ran this {once_per}."}
    return _run_out(run)
