"""
Automation: API keys for external tools and signed outbound webhooks.

n8n, Zapier, Make or a custom agent connect in two ways:

* they RECEIVE events (appointment booked, payment received, daily report,
  post published ...) on a webhook URL an administrator registers, and
* they CALL the automation API (/automation/v1/...) with an API key.

Security:
* API keys are random, shown once and stored only as a SHA-256 hash.
* Every webhook body is signed with HMAC-SHA256 so the receiver can check
  that it really comes from this server.
* Webhook URLs that point to private or local addresses are refused in
  production (server-side request forgery), unless the host is listed in
  AUTOMATION_ALLOWED_HOSTS.
* Events carry ids and operational facts. Reasons for a visit, assessments
  and prescriptions are never sent. Contact details are sent only to
  endpoints where the administrator switched that on.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ApiKey, WebhookDelivery, WebhookEndpoint
from app.services import http_client

logger = logging.getLogger("skyntri.automation")

API_KEY_PREFIX = "sky_"
SCOPES: dict[str, str] = {
    "read:summary": "Read the daily clinic summary (counts only)",
    "read:appointments": "List appointments (with patient contact details)",
    "write:appointments": "Confirm or cancel appointments",
    "write:posts": "Create and publish clinic posts",
    "run:agents": "Start the built-in agents",
}

EVENTS: dict[str, str] = {
    "appointment.created": "A patient booked an appointment",
    "appointment.updated": "An appointment was confirmed, completed or cancelled",
    "appointment.reminder": "Reminder for an appointment in the next 24 hours",
    "payment.succeeded": "An online payment was received",
    "order.created": "A shop order was placed",
    "doctor.applied": "A doctor applied and waits for approval",
    "post.published": "A clinic post was published",
    "report.daily": "The daily clinic report is ready",
    "test.ping": "Test event sent from the admin panel",
}

MAX_CONSECUTIVE_FAILURES = 20
KEEP_DELIVERIES = 500

# "thread" in the running app; tests switch to "inline".
DELIVERY_MODE = "thread"


# ============================================================
# API keys
# ============================================================

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_api_key(db: Session, name: str, scopes: list[str], created_by: str | None) -> tuple[ApiKey, str]:
    """Returns the stored row and the plain key (shown to the admin once)."""
    unknown = [s for s in scopes if s not in SCOPES]
    if unknown:
        raise ValueError(f"Unknown scope: {unknown[0]}")

    plain = API_KEY_PREFIX + secrets.token_urlsafe(32)
    row = ApiKey(
        name=name.strip(),
        prefix=plain[:10],
        key_hash=hash_api_key(plain),
        scopes=",".join(sorted(set(scopes))),
        created_by=created_by,
    )
    db.add(row)
    return row, plain


def find_api_key(db: Session, plain: str) -> ApiKey | None:
    if not plain or not plain.startswith(API_KEY_PREFIX) or len(plain) > 200:
        return None
    row = db.query(ApiKey).filter(ApiKey.key_hash == hash_api_key(plain)).first()
    if row is None or row.revoked_at is not None:
        return None
    return row


def key_scopes(row: ApiKey) -> set[str]:
    return {s for s in (row.scopes or "").split(",") if s}


# ============================================================
# Webhook URL safety
# ============================================================

class UnsafeWebhookUrl(ValueError):
    pass


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    )


def validate_webhook_url(url: str) -> str:
    """Return the cleaned URL or raise UnsafeWebhookUrl with a readable reason."""
    url = (url or "").strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in {"http", "https"} or not host:
        raise UnsafeWebhookUrl("Enter a full URL that starts with https://")
    if parsed.username or parsed.password:
        raise UnsafeWebhookUrl("The URL must not contain a user name or password.")
    if len(url) > 500:
        raise UnsafeWebhookUrl("The URL is too long.")

    allowed = host in settings.automation_allowed_host_list
    if allowed or not settings.is_production:
        return url

    if parsed.scheme != "https":
        raise UnsafeWebhookUrl("Webhook URLs must use https://")

    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise UnsafeWebhookUrl("The host name could not be found.") from None

    if not infos or not all(_is_public_ip(info[4][0]) for info in infos):
        raise UnsafeWebhookUrl(
            "This address is private or local. Add the host to AUTOMATION_ALLOWED_HOSTS to allow it."
        )
    return url


# ============================================================
# Signing
# ============================================================

def endpoint_secret(endpoint_id: str) -> str:
    """
    Signing secret of one endpoint, derived from SECRET_KEY so it does not
    have to be stored. Changing SECRET_KEY changes every webhook secret.
    """
    key = hashlib.sha256(("skyntri-webhook:" + settings.secret_key).encode("utf-8")).digest()
    digest = hmac.new(key, endpoint_id.encode("utf-8"), hashlib.sha256).digest()
    return "whsec_" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode("ascii") + b"." + body
    return "sha256=" + hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


# ============================================================
# Events
# ============================================================

def _wants(endpoint: WebhookEndpoint, event: str) -> bool:
    wanted = {e.strip() for e in (endpoint.events or "*").split(",") if e.strip()}
    return "*" in wanted or event in wanted


def emit(db: Session, event: str, data: dict, contact: dict | None = None) -> int:
    """
    Queue `event` for every active endpoint that subscribed to it and start
    delivery. Call AFTER the change it describes has been committed.

    `contact` (patient name / e-mail / phone) is added only for endpoints
    with include_contact switched on. Returns the number of deliveries.
    Never raises: automation must not break the request that caused it.
    """
    try:
        endpoints = [
            e for e in db.query(WebhookEndpoint).filter(WebhookEndpoint.is_active.is_(True)).all()
            if _wants(e, event)
        ]
        if not endpoints:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        ids = []
        for endpoint in endpoints:
            payload = dict(data)
            if contact and endpoint.include_contact:
                payload["contact"] = contact
            envelope = {"id": uuid.uuid4().hex, "event": event, "created_at": now, "data": payload}
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id, event=event, payload=json.dumps(envelope, default=str)
            )
            db.add(delivery)
            db.flush()
            ids.append(delivery.id)
        db.commit()

        if DELIVERY_MODE == "inline":
            deliver(db, ids)
        else:
            bind = db.get_bind()
            threading.Thread(target=_deliver_in_thread, args=(bind, ids), daemon=True).start()
        return len(ids)
    except Exception:
        db.rollback()
        logger.exception("webhook_emit_failed", extra={"event": "webhook_emit_failed", "webhook_event": event})
        return 0


def _deliver_in_thread(bind, delivery_ids: list[str]) -> None:
    session = Session(bind=bind)
    try:
        deliver(session, delivery_ids)
    except Exception:
        logger.exception("webhook_delivery_failed", extra={"event": "webhook_delivery_failed"})
    finally:
        session.close()


def deliver(db: Session, delivery_ids: list[str]) -> None:
    for delivery_id in delivery_ids:
        delivery = db.get(WebhookDelivery, delivery_id)
        endpoint = db.get(WebhookEndpoint, delivery.endpoint_id) if delivery else None
        if delivery is None or endpoint is None:
            continue

        body = delivery.payload.encode("utf-8")
        timestamp = str(int(time.time()))
        status_code, error = None, None

        try:
            url = validate_webhook_url(endpoint.url)
            response = http_client.send(
                "POST",
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Skyntri-Event": delivery.event,
                    "X-Skyntri-Delivery": delivery.id,
                    "X-Skyntri-Timestamp": timestamp,
                    "X-Skyntri-Signature": sign(endpoint_secret(endpoint.id), timestamp, body),
                },
                timeout=settings.webhook_timeout_seconds,
            )
            status_code = response.status
            if not response.ok:
                error = f"HTTP {response.status}"
        except UnsafeWebhookUrl as exc:
            error = str(exc)[:200]
        except http_client.HttpError as exc:
            error = str(exc)[:200]

        delivery.ok = error is None
        delivery.status_code = status_code
        delivery.error = error
        endpoint.last_delivery_at = datetime.now(timezone.utc)
        endpoint.last_status = "ok" if delivery.ok else (error or "failed")
        endpoint.failure_count = 0 if delivery.ok else (endpoint.failure_count or 0) + 1
        if endpoint.failure_count >= MAX_CONSECUTIVE_FAILURES:
            endpoint.is_active = False
        db.commit()

    _prune(db)


def _prune(db: Session) -> None:
    try:
        cutoff = (
            db.query(WebhookDelivery.created_at)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(KEEP_DELIVERIES)
            .limit(1)
            .scalar()
        )
        if cutoff is not None:
            db.query(WebhookDelivery).filter(WebhookDelivery.created_at < cutoff).delete(synchronize_session=False)
            db.commit()
    except Exception:  # pragma: no cover - pruning must never break delivery
        db.rollback()
