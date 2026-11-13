"""Audit trail for administrator, doctor and automation actions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record(db: Session, actor: str, action: str, target: str | None = None, detail: str | None = None) -> None:
    """Add an audit row to the current transaction (the caller commits)."""
    db.add(AuditEvent(actor=actor, action=action, target=target, detail=(detail or None) and detail[:2000]))
