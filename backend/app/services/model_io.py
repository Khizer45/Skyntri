"""
Shared image preparation for the trained models.

Exactly mirrors the notebooks in ml/notebooks/:
    RGB (EXIF-rotated) -> optional face crop -> bilinear resize -> float32 0..255
    (no /255: Keras EfficientNet rescales inside the model)
and optional test-time augmentation (horizontal flip, predictions averaged).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


def largest_face_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    """(x, y, w, h) of the largest frontal face in original pixel coordinates."""
    from app.services.image_gate import _face_detector

    detector = _face_detector()
    if detector is None:
        return None

    import cv2

    gray = image.convert("L")
    scale = 1.0
    if max(gray.size) > 800:
        scale = 800.0 / max(gray.size)
        gray = gray.resize((int(gray.width * scale), int(gray.height * scale)), Image.Resampling.BILINEAR)

    arr = np.asarray(gray, dtype=np.uint8)
    min_side = max(40, int(min(arr.shape) * 0.12))
    faces = detector.detectMultiScale(cv2.equalizeHist(arr), 1.1, 5, minSize=(min_side, min_side))
    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return int(x / scale), int(y / scale), int(w / scale), int(h / scale)


def crop_to_face(image: Image.Image, margin: float) -> Image.Image:
    box = largest_face_box(image)
    if box is None:
        return image  # close-ups without a detectable face are used as-is (same as training)
    x, y, w, h = box
    m = int(margin * max(w, h))
    return image.crop((max(0, x - m), max(0, y - m), min(image.width, x + w + m), min(image.height, y + h + m)))


def prepare_batch(
    image_path: str | Path,
    size: int,
    face_crop: bool = False,
    face_margin: float = 0.35,
    tta: bool = False,
) -> np.ndarray:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image was not found at: {path}")

    try:
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc
    except OSError as exc:
        raise ValueError("The uploaded image could not be opened.") from exc

    if face_crop:
        image = crop_to_face(image, face_margin)

    image = image.resize((size, size), Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32)

    if array.shape != (size, size, 3):
        raise ValueError("The image could not be converted to the required RGB format.")

    batch = [array]
    if tta:
        batch.append(array[:, ::-1, :])
    return np.stack(batch).astype(np.float32)
