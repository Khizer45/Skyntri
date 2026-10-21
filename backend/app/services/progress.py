from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


# ============================================================
# Configuration
# ============================================================

MIN_IMAGE_DIMENSION = 64

REDNESS_WEIGHT = 0.40
AREA_WEIGHT = 0.35
TEXTURE_WEIGHT = 0.25

IMPROVEMENT_THRESHOLD = 10.0
DETERIORATION_THRESHOLD = -10.0

MAX_COMPONENT_CHANGE = 100.0


# ============================================================
# Image loading / validation
# ============================================================

def _load_image(image_path: str | Path) -> np.ndarray:
    """
    Load and validate an image using OpenCV.

    Raises:
        FileNotFoundError:
            If the image path does not exist.

        ValueError:
            If the image cannot be read or is too small.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}"
        )

    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "Could not read the progress image."
        )

    height, width = image.shape[:2]

    if (
        width < MIN_IMAGE_DIMENSION
        or height < MIN_IMAGE_DIMENSION
    ):
        raise ValueError(
            "Progress images are too small for a reliable comparison."
        )

    return image


# ============================================================
# Image size alignment
# ============================================================

def _resize_to_same_size(
    before: np.ndarray,
    after: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Resize the after image to the before image dimensions.

    Only geometric resizing is performed here. No artificial
    lighting or contrast normalization is applied because such
    processing could alter the visual metrics being compared.
    """

    height, width = before.shape[:2]

    if after.shape[:2] == before.shape[:2]:
        return before, after

    after_resized = cv2.resize(
        after,
        (width, height),
        interpolation=cv2.INTER_AREA,
    )

    return before, after_resized


# ============================================================
# Redness metric
# ============================================================

def _redness_score(image: np.ndarray) -> float:
    """
    Estimate the percentage of visibly reddish pixels.

    This is an image-processing heuristic and is NOT a clinical
    redness measurement.
    """

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV,
    )

    lower_red_1 = np.array(
        [0, 45, 50],
        dtype=np.uint8,
    )

    upper_red_1 = np.array(
        [15, 255, 255],
        dtype=np.uint8,
    )

    lower_red_2 = np.array(
        [165, 45, 50],
        dtype=np.uint8,
    )

    upper_red_2 = np.array(
        [179, 255, 255],
        dtype=np.uint8,
    )

    mask_1 = cv2.inRange(
        hsv,
        lower_red_1,
        upper_red_1,
    )

    mask_2 = cv2.inRange(
        hsv,
        lower_red_2,
        upper_red_2,
    )

    redness_mask = cv2.bitwise_or(
        mask_1,
        mask_2,
    )

    return float(
        np.mean(redness_mask > 0) * 100.0
    )


# ============================================================
# Texture metric
# ============================================================

def _texture_score(image: np.ndarray) -> float:
    """
    Estimate visible local texture variation.

    Higher values indicate greater local intensity variation.

    This is a visual heuristic and should not be interpreted as
    a clinical skin-texture measurement.
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0,
    )

    texture = cv2.absdiff(
        gray,
        blurred,
    )

    return float(
        np.mean(texture)
    )


# ============================================================
# Affected-area metric
# ============================================================

def _affected_area_score(image: np.ndarray) -> float:
    """
    Estimate visible affected-area patterns using saturation
    and edge information.

    IMPORTANT:
    This is NOT a medical lesion detector.

    The value should only be interpreted as an estimated visual
    affected-area pattern for before/after comparison.
    """

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV,
    )

    saturation_mask = cv2.inRange(
        hsv,
        np.array(
            [0, 45, 40],
            dtype=np.uint8,
        ),
        np.array(
            [179, 255, 255],
            dtype=np.uint8,
        ),
    )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    edges = cv2.Canny(
        gray,
        80,
        160,
    )

    combined = cv2.bitwise_and(
        saturation_mask,
        edges,
    )

    kernel = np.ones(
        (3, 3),
        dtype=np.uint8,
    )

    combined = cv2.morphologyEx(
        combined,
        cv2.MORPH_OPEN,
        kernel,
    )

    return float(
        np.mean(combined > 0) * 100.0
    )


# ============================================================
# Percentage change
# ============================================================

def _percentage_change(
    before: float,
    after: float,
) -> float:
    """
    Calculate percentage reduction from before to after.

    Positive value:
        The metric decreased, interpreted as improvement.

    Negative value:
        The metric increased, interpreted as deterioration.

    If the baseline is extremely small, the percentage change is
    considered unreliable and 0 is returned.
    """

    if before <= 0.0001:
        return 0.0

    change = (
        (before - after)
        / before
    ) * 100.0

    if not np.isfinite(change):
        return 0.0

    return float(change)


# ============================================================
# Safe clipping
# ============================================================

def _clip_change(value: float) -> float:
    """
    Keep a metric change inside the supported -100 to +100 range.
    """

    return float(
        np.clip(
            value,
            -MAX_COMPONENT_CHANGE,
            MAX_COMPONENT_CHANGE,
        )
    )


# ============================================================
# Status
# ============================================================

def _get_progress_status(
    improvement_change: float,
) -> str:
    """
    Convert weighted visual change into a user-facing status.
    """

    if improvement_change >= IMPROVEMENT_THRESHOLD:
        return "Improved"

    if improvement_change <= DETERIORATION_THRESHOLD:
        return "Deteriorated"

    return "No Significant Change"


# ============================================================
# Observation generation
# ============================================================

def _redness_observation(change: float) -> str:
    if change >= IMPROVEMENT_THRESHOLD:
        return (
            "Visible redness appears reduced compared "
            "with the previous image."
        )

    if change <= DETERIORATION_THRESHOLD:
        return (
            "Visible redness appears increased compared "
            "with the previous image."
        )

    return (
        "No significant change in visible redness "
        "was detected."
    )


def _area_observation(change: float) -> str:
    if change >= IMPROVEMENT_THRESHOLD:
        return (
            "The estimated affected-area pattern appears reduced."
        )

    if change <= DETERIORATION_THRESHOLD:
        return (
            "The estimated affected-area pattern appears increased."
        )

    return (
        "No significant change in the estimated affected-area "
        "pattern was detected."
    )


def _texture_observation(change: float) -> str:
    if change >= IMPROVEMENT_THRESHOLD:
        return (
            "Visible skin texture variation appears reduced."
        )

    if change <= DETERIORATION_THRESHOLD:
        return (
            "Visible skin texture variation appears increased."
        )

    return (
        "No significant change in visible skin texture "
        "was detected."
    )


# ============================================================
# Main progress calculation
# ============================================================

def compute_progress_score(
    before_image_path: str | Path,
    after_image_path: str | Path,
) -> dict:
    """
    Compare before/after skin images using OpenCV.

    Visual metrics:
        - visible redness
        - estimated affected-area pattern
        - visible texture variation

    Weighted model:
        Redness       = 40%
        Affected area = 35%
        Texture       = 25%

    Returns:
        {
            "status": str,
            "score": float,
            "improvement_change": float,
            "observations": list[str],
            "metrics": {
                "redness": {...},
                "affected_area": {...},
                "texture": {...}
            }
        }

    IMPORTANT:
    This is a visual comparison estimate. It is not a clinical
    measurement, diagnosis, or medical assessment.
    """

    # ---------------------------------------------------------
    # Load images
    # ---------------------------------------------------------

    before = _load_image(
        before_image_path
    )

    after = _load_image(
        after_image_path
    )

    # ---------------------------------------------------------
    # Align dimensions
    # ---------------------------------------------------------

    before, after = _resize_to_same_size(
        before,
        after,
    )

    # ---------------------------------------------------------
    # Calculate visual metrics
    # ---------------------------------------------------------

    before_redness = _redness_score(
        before
    )

    after_redness = _redness_score(
        after
    )

    before_texture = _texture_score(
        before
    )

    after_texture = _texture_score(
        after
    )

    before_area = _affected_area_score(
        before
    )

    after_area = _affected_area_score(
        after
    )

    # ---------------------------------------------------------
    # Calculate percentage changes
    # ---------------------------------------------------------

    redness_change = _percentage_change(
        before_redness,
        after_redness,
    )

    area_change = _percentage_change(
        before_area,
        after_area,
    )

    texture_change = _percentage_change(
        before_texture,
        after_texture,
    )

    # ---------------------------------------------------------
    # Clip metric changes
    # ---------------------------------------------------------

    redness_component = _clip_change(
        redness_change
    )

    area_component = _clip_change(
        area_change
    )

    texture_component = _clip_change(
        texture_change
    )

    # ---------------------------------------------------------
    # Weighted visual change
    # ---------------------------------------------------------

    improvement_change = (
        redness_component * REDNESS_WEIGHT
        + area_component * AREA_WEIGHT
        + texture_component * TEXTURE_WEIGHT
    )

    improvement_change = _clip_change(
        improvement_change
    )

    # ---------------------------------------------------------
    # User-facing progress score
    # ---------------------------------------------------------
    #
    # 50 = approximately unchanged
    # >50 = estimated visual improvement
    # <50 = estimated visual deterioration
    #
    # This is an application score, NOT a medical percentage.
    # ---------------------------------------------------------

    score = (
        50.0
        + improvement_change * 0.5
    )

    score = float(
        np.clip(
            score,
            0.0,
            100.0,
        )
    )

    score = round(
        score,
        1,
    )

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    status = _get_progress_status(
        improvement_change
    )

    # ---------------------------------------------------------
    # Observations
    # ---------------------------------------------------------

    observations = [
        _redness_observation(
            redness_change
        ),
        _area_observation(
            area_change
        ),
        _texture_observation(
            texture_change
        ),
    ]

    # ---------------------------------------------------------
    # Return
    # ---------------------------------------------------------

    return {
        "status": status,
        "score": score,
        "improvement_change": round(
            improvement_change,
            2,
        ),
        "observations": observations,
        "metrics": {
            "redness": {
                "before": round(
                    before_redness,
                    2,
                ),
                "after": round(
                    after_redness,
                    2,
                ),
                "change": round(
                    redness_change,
                    2,
                ),
            },
            "affected_area": {
                "before": round(
                    before_area,
                    2,
                ),
                "after": round(
                    after_area,
                    2,
                ),
                "change": round(
                    area_change,
                    2,
                ),
            },
            "texture": {
                "before": round(
                    before_texture,
                    2,
                ),
                "after": round(
                    after_texture,
                    2,
                ),
                "change": round(
                    texture_change,
                    2,
                ),
            },
        },
    }