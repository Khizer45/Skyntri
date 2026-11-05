"""
Private file delivery through short-lived signed URLs (SK-04,
SEC-DATA-002..004, SEC-UP-010).

Signed URLs are only generated inside owner-scoped API responses, expire
after SIGNED_URL_TTL_SECONDS, and are bound to one exact file path.
Reports are NOT served here; they use the authenticated, owner-checked
`/reports/{id}/download` endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.security import verify_file_signature
from app.services.uploads import PUBLIC_SUBFOLDERS, resolve_upload_url

router = APIRouter(prefix="/files", tags=["files"])

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_SERVABLE_FOLDERS = {"analyses", "avatars", "progress", "ingredient_scans", "ingredients_scans", "products"}


@router.get("/products/{filename}")
def get_product_image(filename: str):
    """Product photos are public catalogue content (no signature needed)."""
    path = resolve_upload_url(f"/uploads/products/{filename}")
    if path is None or not path.is_file() or path.suffix.lower() not in _MEDIA_TYPES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return FileResponse(
        path=str(path),
        media_type=_MEDIA_TYPES[path.suffix.lower()],
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{folder}/{filename}")
def get_private_file(
    folder: str,
    filename: str,
    exp: int = Query(...),
    sig: str = Query(..., max_length=200),
):
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    if folder not in _SERVABLE_FOLDERS or folder in PUBLIC_SUBFOLDERS:
        raise not_found

    relative = f"{folder}/{filename}"

    if not verify_file_signature(relative, exp, sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file link is invalid or has expired.",
        )

    path = resolve_upload_url(f"/uploads/{relative}")

    if path is None or not path.is_file():
        raise not_found

    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise not_found

    return FileResponse(
        path=str(path),
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
