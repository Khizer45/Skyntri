"""Shared helpers for tests: synthetic images (no personal photos in the repo)."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image


def make_skin_closeup(size: int = 320, seed: int = 0) -> Image.Image:
    """Synthetic close-up of skin: skin tone, soft texture and a few spots."""
    rng = np.random.default_rng(seed)
    base = np.array([198, 140, 112], dtype=np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    shading = 1.0 - 0.15 * ((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size**2 / 2)
    texture = rng.normal(0, 6, (size, size, 1))
    img = base * shading[..., None] + texture
    for _ in range(12):
        cx, cy = rng.integers(10, size - 10, 2)
        r = rng.integers(3, 7)
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r**2
        img[mask] = img[mask] * np.array([1.05, 0.8, 0.8])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def make_document(size: int = 320) -> Image.Image:
    """Synthetic black-on-white text page."""
    img = np.full((size, size, 3), 245, dtype=np.uint8)
    for row in range(20, size - 20, 18):
        for col in range(20, size - 40, 9):
            if (row + col) % 5:
                img[row : row + 8, col : col + 6] = 30
    return Image.fromarray(img)


def make_screen(size: int = 320) -> Image.Image:
    """Synthetic laptop/screen-like object: dark bezel, blue UI, keys."""
    img = np.full((size, size, 3), 60, dtype=np.uint8)
    img[30:190, 30:290] = [35, 90, 170]
    img[50:70, 50:270] = [230, 230, 235]
    for row in range(210, 300, 22):
        for col in range(30, 290, 26):
            img[row : row + 16, col : col + 20] = [25, 25, 28]
    return Image.fromarray(img)


def to_bytes(image: Image.Image, fmt: str = "JPEG") -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=fmt, quality=92)
    return buffer.getvalue()


def make_jpeg_bytes() -> bytes:
    return to_bytes(make_skin_closeup())
