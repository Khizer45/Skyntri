"""
Database-backed sliding-window rate limiting (SK-07, SK-13, SEC-APP-005).

The counters live in the shared database (`rate_limit_events`), so limits
are consistent across Uvicorn workers, restarts and multiple instances that
share the same PostgreSQL database. Accounts are never permanently locked:
every limit is a rolling time window, which avoids lock-out denial of
service.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RateLimitEvent

# Events older than this are deleted opportunistically.
_RETENTION = timedelta(hours=25)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_key(key: str) -> str:
    return hashlib.sha256(
        ("skyntri-rl:" + key.strip().lower()).encode("utf-8")
    ).hexdigest()


def client_ip(request: Request | None) -> str:
    """
    Best-effort client IP.

    X-Forwarded-For is NOT trusted here because it is client controlled.
    When running behind a trusted proxy, start Uvicorn with
    `--proxy-headers --forwarded-allow-ips=<proxy ip>` so request.client
    already contains the real address.
    """
    if request is None or request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def count_recent(db: Session, bucket: str, key: str, window: timedelta) -> int:
    cutoff = _utcnow() - window
    return int(
        db.execute(
            select(func.count(RateLimitEvent.id)).where(
                RateLimitEvent.bucket == bucket,
                RateLimitEvent.key_hash == _hash_key(key),
                RateLimitEvent.created_at >= cutoff,
            )
        ).scalar_one()
    )


def record_event(db: Session, bucket: str, key: str) -> None:
    db.add(RateLimitEvent(bucket=bucket, key_hash=_hash_key(key)))
    db.commit()

    # Cheap opportunistic pruning (about 1 in 50 writes).
    if random.random() < 0.02:
        prune_old_events(db)


def clear_events(db: Session, bucket: str, key: str) -> None:
    db.execute(
        delete(RateLimitEvent).where(
            RateLimitEvent.bucket == bucket,
            RateLimitEvent.key_hash == _hash_key(key),
        )
    )
    db.commit()


def prune_old_events(db: Session) -> None:
    try:
        db.execute(
            delete(RateLimitEvent).where(
                RateLimitEvent.created_at < _utcnow() - _RETENTION
            )
        )
        db.commit()
    except Exception:  # pragma: no cover - pruning must never break requests
        db.rollback()


def is_limited(
    db: Session,
    bucket: str,
    key: str,
    limit: int,
    window: timedelta,
) -> bool:
    if not settings.rate_limit_enabled or limit <= 0:
        return False
    return count_recent(db, bucket, key, window) >= limit


def too_many_requests(message: str | None = None, retry_after: int = 60) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=message or "Too many requests. Please wait a few minutes and try again.",
        headers={"Retry-After": str(retry_after)},
    )


def enforce(
    db: Session,
    bucket: str,
    key: str,
    limit: int,
    window: timedelta = timedelta(hours=1),
    message: str | None = None,
) -> None:
    """
    Count this action and raise HTTP 429 when the limit for the window has
    been reached. The attempt that is rejected is not counted, so a client
    regains access as soon as older events leave the window.
    """
    if not settings.rate_limit_enabled or limit <= 0:
        return

    if is_limited(db, bucket, key, limit, window):
        raise too_many_requests(message, retry_after=int(window.total_seconds() // 4) or 60)

    record_event(db, bucket, key)
