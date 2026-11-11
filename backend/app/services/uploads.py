"""
Private upload handling (SK-04, SK-12, SEC-UP-001..010, SEC-DATA-002..004).

* Files are written to a PRIVATE directory (UPLOAD_DIR) that is never
  mounted as public static content.
* The database keeps the internal reference `/uploads/<folder>/<name>`
  (unchanged format, so historical records stay valid).
* Browsers receive short-lived signed URLs (`/files/...?exp=&sig=`)
  produced by `signed_url()` only for records the requester owns.
* Images are validated by decoding them: real format, dimensions, pixel
  count, animation. Client filename/MIME type are never trusted.
"""

from __future__ import annotations

import uuid
import warnings
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.security import sign_file_path

# Real decoded format -> stored extension.
ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/webp",
}

# Kept for backward compatibility with older imports/tests.
MAX_FILE_SIZE_BYTES = settings.max_upload_bytes

ALLOWED_SUBFOLDERS = {
    "analyses",
    "avatars",
    "progress",
    "ingredient_scans",
    "ingredients_scans",
    "reports",
    "products",
    "chat_images",
}

# Folders whose files are public catalogue content (product photos), served
# without a signature. User photos are NEVER placed here.
PUBLIC_SUBFOLDERS = {"products"}

INTERNAL_PREFIX = "/uploads/"
PUBLIC_FILES_PREFIX = "/files/"

# Protects Pillow against decompression bombs (SEC-UP-004).
Image.MAX_IMAGE_PIXELS = settings.max_image_pixels


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _validate_subfolder(subfolder: str) -> str:
    if subfolder not in ALLOWED_SUBFOLDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload destination.",
        )
    return subfolder


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def validate_image_file(path: Path) -> str:
    """
    Decode the stored file and return its real format.

    Raises HTTP 400 for anything that is not a supported, non-animated,
    reasonably sized raster image.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(path) as image:
                image_format = (image.format or "").upper()

                if image_format not in ALLOWED_FORMATS:
                    raise _bad_request(
                        "Unsupported format. Please upload a JPEG, PNG, or WebP image."
                    )

                width, height = image.size

                if getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1:
                    raise _bad_request("Animated images are not supported.")

                # verify() checks structure; load() fully decodes pixels.
                image.verify()

            with Image.open(path) as image:
                image.load()

    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise _bad_request("The image dimensions are too large.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise _bad_request(
            "The uploaded file is not a valid image. Please upload a JPEG, PNG, or WebP photo."
        ) from exc

    if width < settings.min_image_side or height < settings.min_image_side:
        raise _bad_request(
            f"The image is too small. Please upload a photo at least "
            f"{settings.min_image_side}x{settings.min_image_side} pixels."
        )

    if (
        width > settings.max_image_side
        or height > settings.max_image_side
        or width * height > settings.max_image_pixels
    ):
        raise _bad_request("The image dimensions are too large.")

    return image_format


def save_upload(file: UploadFile, subfolder: str) -> str:
    """
    Validate and store an uploaded image privately.

    Returns the internal reference `/uploads/<subfolder>/<random>.<ext>`.
    """
    if file is None:
        raise _bad_request("Please upload an image.")

    if not file.filename:
        raise _bad_request("The uploaded file has no filename.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise _bad_request("Unsupported format. Please upload JPEG, PNG, or WebP.")

    safe_subfolder = _validate_subfolder(subfolder)

    dest_dir = settings.upload_path / safe_subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Random server-side name; the final extension comes from the decoded
    # format, never from the client.
    temp_path = dest_dir / f".tmp-{uuid.uuid4().hex}"
    final_path: Path | None = None

    size = 0
    chunk_size = 1024 * 1024

    try:
        with temp_path.open("wb") as buffer:
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    limit_mb = settings.max_upload_bytes // (1024 * 1024)
                    raise _bad_request(f"Image exceeds the {limit_mb}MB size limit.")
                buffer.write(chunk)

        if size == 0:
            raise _bad_request("The uploaded image is empty.")

        image_format = validate_image_file(temp_path)

        final_path = dest_dir / f"{uuid.uuid4().hex}{ALLOWED_FORMATS[image_format]}"

        upload_root = settings.upload_path.resolve()
        final_path.resolve().relative_to(upload_root)

        temp_path.replace(final_path)

    except HTTPException:
        _safe_unlink(temp_path)
        _safe_unlink(final_path)
        raise
    except Exception as exc:
        _safe_unlink(temp_path)
        _safe_unlink(final_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The image upload could not be completed.",
        ) from exc

    return f"{INTERNAL_PREFIX}{safe_subfolder}/{final_path.name}"


def save_image_bytes(data: bytes, subfolder: str) -> str:
    """
    Store image bytes produced by the server (e.g. a generated illustration)
    with the same validation and private storage as uploads.
    """
    if not data or len(data) > settings.max_upload_bytes:
        raise _bad_request("The image could not be stored.")

    safe_subfolder = _validate_subfolder(subfolder)
    dest_dir = settings.upload_path / safe_subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    temp_path = dest_dir / f".tmp-{uuid.uuid4().hex}"
    try:
        temp_path.write_bytes(data)
        image_format = validate_image_file(temp_path)
        final_path = dest_dir / f"{uuid.uuid4().hex}{ALLOWED_FORMATS[image_format]}"
        temp_path.replace(final_path)
    except HTTPException:
        _safe_unlink(temp_path)
        raise
    except Exception as exc:
        _safe_unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The image could not be stored.",
        ) from exc

    return f"{INTERNAL_PREFIX}{safe_subfolder}/{final_path.name}"


# ============================================================
# Reference helpers
# ============================================================

def resolve_upload_url(image_url: str | None) -> Path | None:
    """
    Map an internal `/uploads/<folder>/<name>` reference to a path inside
    the private upload directory. Returns None for anything else.
    """
    if not image_url or not image_url.startswith(INTERNAL_PREFIX):
        return None

    relative = image_url[len(INTERNAL_PREFIX):]
    parts = relative.split("/")

    if len(parts) != 2 or not all(parts) or parts[0] not in ALLOWED_SUBFOLDERS:
        return None

    if any(part in {".", ".."} or "\\" in part for part in parts):
        return None

    root = settings.upload_path.resolve()
    candidate = (settings.upload_path / parts[0] / parts[1]).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        return None

    return candidate


def delete_upload(image_url: str | None) -> None:
    _safe_unlink(resolve_upload_url(image_url))


def signed_url(image_url: str | None) -> str | None:
    """
    Convert a stored reference into a short-lived signed URL path.

    Only call this for records that belong to the requesting user; the
    response models do this automatically for owner-scoped queries.
    Values that are not internal upload references are returned as-is.
    """
    if not image_url:
        return image_url

    if not image_url.startswith(INTERNAL_PREFIX):
        return image_url

    relative = image_url[len(INTERNAL_PREFIX):]

    if relative.split("/", 1)[0] in PUBLIC_SUBFOLDERS:
        return f"{PUBLIC_FILES_PREFIX}{quote(relative)}"

    expires, signature = sign_file_path(relative)

    return (
        f"{PUBLIC_FILES_PREFIX}{quote(relative)}"
        f"?exp={expires}&sig={quote(signature)}"
    )
