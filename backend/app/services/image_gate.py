"""
Input eligibility gate for skin analysis (ML-01, SEC-ML-001..005).

Runs BEFORE any condition model:

    1. decode (already validated by uploads.validate_image_file)
    2. image-quality checks  -> too small / too dark / overexposed / blurry
    3. skin-vs-non-skin      -> trained gate model if present, otherwise the
                                interim colour/region heuristic below
    4. decision              -> accepted | rejected | uncertain

If the decision is not "accepted" the condition classifier is NOT called
and the API returns an abstention with a reason code and guidance.

IMPORTANT LIMITATION
--------------------
The interim heuristic (`skin-gate-heuristic-v1`) is a rule-based skin-colour
and skin-region detector. It blocks the reported failure (phones, laptops,
screens, documents, rooms, landscapes...) in most cases, but it is NOT a
validated classifier: objects with skin-like colours (wood, sand, some food,
some animals) can pass, and very dark/very pale or unusually lit skin can be
rejected. A trained skin/non-skin model with hard negatives must replace it
before public launch. Drop the trained model at SKIN_GATE_MODEL_PATH and it
is used automatically. See docs/ML_INPUT_GATE.md.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.core.config import settings

HEURISTIC_GATE_VERSION = "skin-gate-heuristic-v1"

# ----------------------------------------------------------------------------
# Thresholds (heuristic). Documented in docs/ML_INPUT_GATE.md.
# ----------------------------------------------------------------------------

MIN_SIDE_FOR_ANALYSIS = 128
DARK_LUMA = 35.0
BRIGHT_LUMA = 235.0
MIN_CONTRAST_STD = 4.0
MIN_SHARPNESS = 6.0

SKIN_ACCEPT_RATIO = 0.30
SKIN_ACCEPT_REGION = 0.18
SKIN_REJECT_RATIO = 0.12
GRAY_REJECT_RATIO = 0.70

# Facial scope (Model A): a frontal face must be detected, unless the photo
# is a close-up where skin fills most of the frame.
CLOSEUP_SKIN_RATIO = 0.75
CLOSEUP_SKIN_REGION = 0.60

ANALYSIS_SIZE = 256


@dataclass
class GateResult:
    status: str  # accepted | rejected | uncertain
    reason_code: str
    message: str
    guidance: list[str] = field(default_factory=list)
    gate_version: str = HEURISTIC_GATE_VERSION
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    def public_detail(self) -> dict[str, Any]:
        """Response body for an abstention (no internal scores)."""
        return {
            "code": self.reason_code,
            "status": self.status,
            "message": self.message,
            "guidance": self.guidance,
            "gate_version": self.gate_version,
        }


RETAKE_GUIDANCE = [
    "Use a clear, close-up photo of the skin area (for facial analysis, your face).",
    "Use even, natural light and avoid strong shadows, filters or flash glare.",
    "Hold the camera steady and keep the skin in focus.",
    "Make sure the skin fills most of the photo.",
]

NOT_SKIN = (
    "not_skin_image",
    "This image does not appear to be a skin photo. Please upload a clear skin image.",
)
UNCERTAIN = (
    "uncertain_input",
    "We cannot confidently analyze this image. Please upload another photo.",
)


# ============================================================================
# Image loading
# ============================================================================

def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE), Image.Resampling.BILINEAR)
        return np.asarray(image, dtype=np.uint8)


def _original_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


# ============================================================================
# Quality
# ============================================================================

def _laplacian_variance(gray: np.ndarray) -> float:
    g = gray.astype(np.float32)
    lap = (
        -4.0 * g[1:-1, 1:-1]
        + g[:-2, 1:-1]
        + g[2:, 1:-1]
        + g[1:-1, :-2]
        + g[1:-1, 2:]
    )
    return float(lap.var()) if lap.size else 0.0


def quality_metrics(rgb: np.ndarray) -> dict[str, float]:
    gray = (
        0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    ).astype(np.float32)

    return {
        "luma_mean": float(gray.mean()),
        "luma_std": float(gray.std()),
        "sharpness": _laplacian_variance(gray),
    }


def _quality_problem(size: tuple[int, int], metrics: dict[str, float]) -> GateResult | None:
    width, height = size

    if min(width, height) < MIN_SIDE_FOR_ANALYSIS:
        return GateResult(
            "rejected",
            "image_too_small",
            "The image is too small to analyze. Please upload a larger, clearer photo.",
            RETAKE_GUIDANCE,
        )

    if metrics["luma_mean"] < DARK_LUMA:
        return GateResult(
            "rejected",
            "image_too_dark",
            "The photo is too dark to analyze. Please retake it in brighter, even light.",
            RETAKE_GUIDANCE,
        )

    if metrics["luma_mean"] > BRIGHT_LUMA:
        return GateResult(
            "rejected",
            "image_overexposed",
            "The photo is too bright or washed out. Please retake it without direct glare or flash.",
            RETAKE_GUIDANCE,
        )

    if metrics["luma_std"] < MIN_CONTRAST_STD:
        return GateResult(
            "rejected",
            "image_low_detail",
            "The image has almost no visible detail. Please upload a clear skin photo.",
            RETAKE_GUIDANCE,
        )

    if metrics["sharpness"] < MIN_SHARPNESS:
        return GateResult(
            "rejected",
            "image_too_blurry",
            "The photo looks blurry. Please hold the camera steady and retake it in focus.",
            RETAKE_GUIDANCE,
        )

    return None


# ============================================================================
# Heuristic skin detector
# ============================================================================

def skin_mask(rgb: np.ndarray) -> np.ndarray:
    """
    Combined YCrCb + RGB skin-colour rule (covers light to dark skin tones
    under ordinary lighting). Returns a boolean mask.
    """
    rgbf = rgb.astype(np.float32)
    r, g, b = rgbf[..., 0], rgbf[..., 1], rgbf[..., 2]

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cr = (r - y) * 0.713 + 128.0
    cb = (b - y) * 0.564 + 128.0

    ycrcb_rule = (cr >= 133) & (cr <= 180) & (cb >= 75) & (cb <= 130) & (y >= 25)

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    rgb_rule = (
        (r > 50)
        & (g > 25)
        & (b > 10)
        & ((max_c - min_c) > 12)
        & (r > g)
        & (r > b)
        & (np.abs(r - g) > 8)
    )

    return ycrcb_rule & rgb_rule


def _largest_region_fraction(mask: np.ndarray) -> float:
    """Fraction of the image covered by the largest connected skin region."""
    total = mask.size
    if total == 0 or not mask.any():
        return 0.0

    try:
        import cv2  # opencv-python-headless (already a backend dependency)

        count, _labels, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8), connectivity=8
        )
        if count <= 1:
            return 0.0
        largest = int(stats[1:, cv2.CC_STAT_AREA].max())
        return largest / float(total)
    except Exception:  # pragma: no cover - fallback without OpenCV
        return float(mask.mean())


def heuristic_skin_metrics(rgb: np.ndarray) -> dict[str, float]:
    mask = skin_mask(rgb)

    rgbf = rgb.astype(np.float32)
    max_c = rgbf.max(axis=2)
    min_c = rgbf.min(axis=2)
    saturation = np.where(max_c > 0, (max_c - min_c) / np.maximum(max_c, 1.0), 0.0)

    return {
        "skin_ratio": float(mask.mean()),
        "skin_region": _largest_region_fraction(mask),
        "gray_ratio": float((saturation < 0.08).mean()),
    }


def _heuristic_decision(metrics: dict[str, float]) -> GateResult:
    skin_ratio = metrics["skin_ratio"]
    region = metrics["skin_region"]

    if metrics["gray_ratio"] >= GRAY_REJECT_RATIO and skin_ratio < SKIN_ACCEPT_RATIO:
        return GateResult("rejected", NOT_SKIN[0], NOT_SKIN[1], RETAKE_GUIDANCE)

    if skin_ratio < SKIN_REJECT_RATIO:
        return GateResult("rejected", NOT_SKIN[0], NOT_SKIN[1], RETAKE_GUIDANCE)

    if skin_ratio >= SKIN_ACCEPT_RATIO and region >= SKIN_ACCEPT_REGION:
        return GateResult("accepted", "accepted", "Image accepted for analysis.")

    return GateResult("uncertain", UNCERTAIN[0], UNCERTAIN[1], RETAKE_GUIDANCE)


# ============================================================================
# Facial scope check (Model A)
# ============================================================================

@lru_cache(maxsize=1)
def _face_detector():
    try:
        import cv2

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            return None
        detector = cv2.CascadeClassifier(str(cascade_path))
        return None if detector.empty() else detector
    except Exception:
        return None


def face_detector_available() -> bool:
    return _face_detector() is not None


def detect_face(path: Path) -> bool | None:
    """True/False when a detector is available, None otherwise."""
    detector = _face_detector()
    if detector is None:
        return None

    import cv2

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        image.thumbnail((640, 640), Image.Resampling.BILINEAR)
        gray = np.asarray(image, dtype=np.uint8)

    min_side = max(40, int(min(gray.shape) * 0.15))
    faces = detector.detectMultiScale(
        cv2.equalizeHist(gray),
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(min_side, min_side),
    )
    return len(faces) > 0


def _facial_scope(path: Path, metrics: dict[str, float], result: GateResult) -> GateResult:
    """
    Model A analyses FACIAL skin concerns only. Accept when a face is
    visible, or when the photo is a facial close-up (skin fills the frame).
    """
    if not result.accepted:
        return result

    face = detect_face(path)
    if face is not None:
        metrics["face_detected"] = 1.0 if face else 0.0

    closeup = (
        metrics.get("skin_ratio", 0.0) >= CLOSEUP_SKIN_RATIO
        and metrics.get("skin_region", 0.0) >= CLOSEUP_SKIN_REGION
    )

    if face or closeup or face is None and metrics.get("skin_ratio", 0.0) >= SKIN_ACCEPT_RATIO:
        return result

    return GateResult(
        "uncertain",
        "face_not_detected",
        "Facial skin analysis needs a clear photo of your face. We could not find a face in this image.",
        [
            "Take a front-facing photo of your face, or a close-up of the facial skin area.",
            *RETAKE_GUIDANCE[1:],
        ],
        result.gate_version,
        metrics,
    )


# ============================================================================
# Optional trained gate model
# ============================================================================

_gate_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load_trained_gate():
    path = settings.skin_gate_model
    if not Path(path).exists():
        return None

    import tensorflow as tf

    model = tf.keras.models.load_model(path, compile=False)
    return model


def trained_gate_available() -> bool:
    return Path(settings.skin_gate_model).exists()


def _trained_gate_probability(path: Path) -> float | None:
    model = _load_trained_gate()
    if model is None:
        return None

    input_shape = model.input_shape
    height = int(input_shape[1] or 224)
    width = int(input_shape[2] or 224)

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        array = np.asarray(image, dtype=np.float32)[None, ...]

    with _gate_lock:
        prediction = np.asarray(model.predict(array, verbose=0)).reshape(-1)

    if prediction.size == 0:
        return None

    return float(np.clip(prediction[0], 0.0, 1.0))


# ============================================================================
# Public entry point
# ============================================================================

def assess_image(path: str | Path, track: str = "facial_concerns") -> GateResult:
    path = Path(path)

    try:
        size = _original_size(path)
        rgb = _load_rgb(path)
    except Exception:
        return GateResult(
            "rejected",
            "invalid_image",
            "The uploaded file could not be read as an image. Please upload a JPEG, PNG, or WebP photo.",
            RETAKE_GUIDANCE,
        )

    metrics = quality_metrics(rgb)

    problem = _quality_problem(size, metrics)
    if problem is not None:
        problem.metrics = metrics
        return problem

    skin_metrics = heuristic_skin_metrics(rgb)
    metrics.update(skin_metrics)

    probability = None
    if trained_gate_available():
        try:
            probability = _trained_gate_probability(path)
        except Exception:
            probability = None

    if probability is not None:
        metrics["gate_probability"] = probability
        version = f"skin-gate-model:{Path(settings.skin_gate_model).name}"

        if probability >= settings.skin_gate_accept_threshold:
            accepted = GateResult("accepted", "accepted", "Image accepted for analysis.", gate_version=version, metrics=metrics)
            return _facial_scope(path, metrics, accepted) if track == "facial_concerns" else accepted

        if probability < settings.skin_gate_reject_threshold:
            return GateResult("rejected", NOT_SKIN[0], NOT_SKIN[1], RETAKE_GUIDANCE, version, metrics)

        return GateResult("uncertain", UNCERTAIN[0], UNCERTAIN[1], RETAKE_GUIDANCE, version, metrics)

    result = _heuristic_decision(skin_metrics)
    result.metrics = metrics

    if track == "facial_concerns":
        result = _facial_scope(path, metrics, result)

    return result


def current_gate_version() -> str:
    if trained_gate_available():
        return f"skin-gate-model:{Path(settings.skin_gate_model).name}"
    return HEURISTIC_GATE_VERSION
