"""Public, non-secret configuration the web app needs before sign-in."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["public"])


@router.get("/config")
def public_config():
    return {
        "clinic_name": settings.clinic_name,
        "currency": settings.shop_currency,
        "timezone": settings.clinic_timezone,
        # A Google client ID is public by design (it is in every sign-in page).
        "google_client_id": settings.google_client_id or None,
    }
