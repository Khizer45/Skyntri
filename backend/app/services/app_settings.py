"""
Settings an administrator can change at run time (stored in app_settings).

A stored value overrides the environment default. Nothing secret is kept
here: API keys and passwords stay in the environment.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AppSetting

# key -> (type, description shown in the admin panel)
EDITABLE: dict[str, tuple[type, str]] = {
    "disease_screening_enabled": (
        bool,
        "Offer skin disease screening to users. Turn on only after a dermatologist "
        "has reviewed the model's results.",
    ),
    "agent_posts_auto_publish": (
        bool,
        "Publish the daily skin-care post automatically. Off: it is saved as a draft.",
    ),
}

_TRUE = {"1", "true", "yes", "on"}


def _default(key: str):
    return getattr(settings, key)


def get_raw(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def get_bool(db: Session, key: str) -> bool:
    raw = get_raw(db, key)
    if raw is None:
        return bool(_default(key))
    return raw.strip().lower() in _TRUE


def get_optional_bool(db: Session, key: str) -> bool | None:
    """None when the administrator has not changed the setting."""
    raw = get_raw(db, key)
    return None if raw is None else raw.strip().lower() in _TRUE


def set_value(db: Session, key: str, value, updated_by: str | None = None) -> None:
    if key not in EDITABLE:
        raise KeyError(key)
    kind, _ = EDITABLE[key]
    text = ("true" if value else "false") if kind is bool else str(value)

    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=text, updated_by=updated_by))
    else:
        row.value = text
        row.updated_by = updated_by


def describe(db: Session) -> list[dict]:
    items = []
    for key, (kind, description) in EDITABLE.items():
        raw = get_raw(db, key)
        items.append(
            {
                "key": key,
                "type": kind.__name__,
                "description": description,
                "value": get_bool(db, key) if kind is bool else (raw if raw is not None else _default(key)),
                "default": _default(key),
                "overridden": raw is not None,
            }
        )
    return items
