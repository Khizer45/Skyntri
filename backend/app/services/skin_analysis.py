from __future__ import annotations

import re
import threading

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

from app.core.config import settings
from app.services.model_io import prepare_batch


# ============================================================
# Configuration
# ============================================================

IMAGE_SIZE = (224, 224)

DATASET3_CLASSES = [
    "Acne",
    "Blackheads",
    "Dark Spots",
    "Dry Skin",
    "Eye bags",
    "Normal Skin",
    "Oily Skin",
    "Pores",
    "Skin Redness",
    "Wrinkles",
]


# ============================================================
# EfficientNetB0 optimized thresholds
# ============================================================
#
# These thresholds were optimized on the Dataset 3 validation
# set by maximizing per-class F1 score.
#
# The same thresholds were then kept unchanged for the final
# Dataset 3 test evaluation.
#
# Final EfficientNetB0 test performance:
#   Micro F1       = 81.17%
#   Macro F1       = 66.73%
#   Weighted F1    = 81.41%
#   Hamming Loss   = 4.03%
#
# ============================================================

DATASET3_THRESHOLDS = {
    "Acne": 0.46,
    "Blackheads": 0.34,
    "Dark Spots": 0.36,
    "Dry Skin": 0.36,
    "Eye bags": 0.27,
    "Normal Skin": 0.29,
    "Oily Skin": 0.36,
    "Pores": 0.38,
    "Skin Redness": 0.27,
    "Wrinkles": 0.20,
}


# ============================================================
# User-facing display names
# ============================================================

DISPLAY_NAMES = {
    "Acne": "Acne",
    "Blackheads": "Blackheads",
    "Dark Spots": "Dark Spots",
    "Dry Skin": "Dry Skin",
    "Eye bags": "Eye Bags",
    "Normal Skin": "Normal Skin",
    "Oily Skin": "Oily Skin",
    "Pores": "Visible Pores",
    "Skin Redness": "Skin Redness",
    "Wrinkles": "Fine Lines & Wrinkles",
}


# ============================================================
# Recommendation mapping
# ============================================================

CONDITION_RECOMMENDATIONS: dict[str, dict[str, list[str]]] = {
    "Acne": {
        "skincare": [
            "Use a gentle cleanser and avoid harsh scrubbing.",
            "Use a salicylic-acid cleanser if your skin tolerates it.",
            "Consider a beginner-friendly acne routine with appropriate actives.",
        ],
        "ingredients": [
            "Salicylic acid",
            "Benzoyl peroxide",
            "Adapalene",
        ],
        "lifestyle": [
            "Avoid picking or squeezing breakouts.",
            "Monitor whether very high-glycemic foods appear to worsen breakouts.",
        ],
        "avoid": [
            "Harsh physical scrubs",
            "Picking or squeezing pimples",
            "Unverified fairness or steroid creams",
        ],
    },

    "Blackheads": {
        "skincare": [
            "Use a gentle cleanser regularly.",
            "A salicylic-acid cleanser may help unclog pores.",
        ],
        "ingredients": [
            "Salicylic acid",
            "Adapalene",
        ],
        "lifestyle": [
            "Keep a consistent cleansing routine.",
            "Avoid repeatedly squeezing clogged pores.",
        ],
        "avoid": [
            "Aggressive pore squeezing",
            "Harsh scrubbing",
        ],
    },

    "Dark Spots": {
        "skincare": [
            "Use daily broad-spectrum sunscreen.",
            "Introduce brightening ingredients gradually.",
        ],
        "ingredients": [
            "Azelaic acid",
            "Glycolic acid",
            "Vitamin C",
        ],
        "lifestyle": [
            "Limit unnecessary direct sun exposure.",
            "Reapply sunscreen when outdoors for extended periods.",
        ],
        "avoid": [
            "Picking irritated areas",
            "Unverified bleaching or fairness creams",
        ],
    },

    "Pores": {
        "skincare": [
            "Use a gentle cleanser.",
            "A niacinamide-based routine may help improve the appearance of pores.",
        ],
        "ingredients": [
            "Niacinamide",
            "Salicylic acid",
        ],
        "lifestyle": [
            "Keep the skin clean without over-cleansing.",
            "Avoid repeatedly squeezing pores.",
        ],
        "avoid": [
            "Aggressive pore extraction",
            "Harsh physical scrubs",
        ],
    },

    "Wrinkles": {
        "skincare": [
            "Use daily broad-spectrum sunscreen.",
            "Keep the skin moisturized.",
            "Introduce retinoids gradually if appropriate for your skin.",
        ],
        "ingredients": [
            "Retinol",
            "Peptides",
        ],
        "lifestyle": [
            "Prioritize consistent sun protection.",
            "Maintain adequate sleep and hydration.",
        ],
        "avoid": [
            "Excessive sun exposure",
            "Harsh repetitive exfoliation",
        ],
    },

    "Dry Skin": {
        "skincare": [
            "Use a gentle cleanser.",
            "Apply moisturizer while the skin is slightly damp.",
        ],
        "ingredients": [
            "Hyaluronic acid",
            "Ceramides",
            "Glycerin",
        ],
        "lifestyle": [
            "Avoid excessively hot water.",
            "Maintain regular hydration.",
        ],
        "avoid": [
            "Over-cleansing",
            "Frequent strong exfoliation",
            "Very hot water",
        ],
    },

    "Skin Redness": {
        "skincare": [
            "Use a gentle, fragrance-minimized routine if irritation is common.",
            "Prioritize barrier-supporting moisturizer and sun protection.",
        ],
        "ingredients": [
            "Centella",
            "Azelaic acid",
        ],
        "lifestyle": [
            "Identify and minimize personal irritation triggers.",
            "Protect the skin from excessive sun exposure.",
        ],
        "avoid": [
            "Harsh scrubbing",
            "Frequent strong exfoliation",
            "Products that repeatedly cause burning or irritation",
        ],
    },

    "Oily Skin": {
        "skincare": [
            "Use a gentle cleanser without over-cleansing.",
            "Choose lightweight, non-comedogenic moisturizing products.",
        ],
        "ingredients": [
            "Niacinamide",
            "Salicylic acid",
        ],
        "lifestyle": [
            "Keep a consistent skincare routine.",
            "Avoid repeatedly washing the face throughout the day.",
        ],
        "avoid": [
            "Over-cleansing",
            "Heavy occlusive products if they consistently clog your skin",
        ],
    },

    "Eye bags": {
        "skincare": [
            "Use a gentle moisturizer around the eye area.",
            "Avoid rubbing or aggressively massaging the eye area.",
        ],
        "ingredients": [
            "Caffeine",
            "Hyaluronic acid",
            "Peptides",
        ],
        "lifestyle": [
            "Maintain consistent sleep.",
            "Avoid unnecessary eye rubbing.",
        ],
        "avoid": [
            "Aggressive rubbing around the eyes",
            "Strong exfoliating acids close to the eyes",
        ],
    },
}


# ============================================================
# Universal recommendations
# ============================================================

UNIVERSAL_SKINCARE = [
    "Use a gentle cleanser suitable for your skin.",
    "Use moisturizer regularly to support the skin barrier.",
]

UNIVERSAL_SUN_PROTECTION = [
    "Use broad-spectrum SPF 30+ sunscreen every day.",
    "Limit prolonged direct sun exposure.",
    "Use shade, protective clothing, or other physical protection when outdoors.",
]

UNIVERSAL_LIFESTYLE = [
    "Maintain consistent sleep and hydration.",
    "Keep your skincare routine simple and consistent.",
]

UNIVERSAL_AVOID = [
    "Avoid harsh scrubbing.",
    "Avoid picking or squeezing skin lesions.",
    "Avoid unverified steroid or fairness creams.",
]

DISCLAIMER = (
    "This result is an AI-estimated assessment of visible skin patterns, "
    "not a medical diagnosis. If a skin concern is persistent, severe, "
    "rapidly changing, painful, infected, or otherwise concerning, consult "
    "a qualified dermatologist."
)


# ============================================================
# Utility helpers
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convert a value to a finite float safely.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if not np.isfinite(number):
        return default

    return number


def _clip_probability(value: Any) -> float:
    """
    Convert model output into a valid probability in [0, 1].
    """
    return float(np.clip(_safe_float(value), 0.0, 1.0))


def _display_name(condition: str) -> str:
    """
    Convert internal condition name into a user-facing name.
    """
    custom = facial_model_config().get("display_names") or {}
    return custom.get(condition) or DISPLAY_NAMES.get(condition, condition)


_TIP_STOPWORDS = frozenset(
    "a an and or the your you to of for if it its is be in on with when "
    "use using avoid avoiding may can regularly daily gently gentle "
    "consider keep try appropriate suitable".split()
)


def _tip_keywords(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stems = set()
    for word in words:
        if word in _TIP_STOPWORDS or len(word) < 3:
            continue
        # crude stemming so "scrubs"/"scrubbing"/"scrub" collapse
        for suffix in ("ing", "es", "s", "ed"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[: -len(suffix)]
                break
        if len(word) >= 5 and word[-1] == word[-2]:
            word = word[:-1]
        stems.add(word)
    return frozenset(stems)


def _unique_preserve_order(
    items: list[str],
    *,
    limit: int | None = None,
) -> list[str]:
    """
    Remove exact and near-duplicate tips while preserving order.

    Two tips are treated as the same advice when one's keywords are a
    subset of the other's, or they share most keywords ("Avoid harsh
    scrubbing" / "Harsh physical scrubs" / "Use a gentle cleanser and
    avoid harsh scrubbing" keep only the first wording).
    """
    seen: set[str] = set()
    kept_keywords: list[frozenset[str]] = []
    result: list[str] = []

    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        keywords = _tip_keywords(item)
        duplicate = False
        for other in kept_keywords:
            if not keywords or not other:
                continue
            overlap = len(keywords & other)
            smaller = min(len(keywords), len(other))
            if (overlap == smaller and smaller >= 2) or overlap / len(keywords | other) >= 0.6:
                duplicate = True
                break
        if duplicate:
            continue
        kept_keywords.append(keywords)
        result.append(item)
        if limit is not None and len(result) >= limit:
            break

    return result


# ============================================================
# Model configuration (classes / thresholds / input size)
# ============================================================
#
# When you retrain Model A with ml/notebooks/01_facial_skin_concerns_
# efficientnet.ipynb, copy the exported files into backend/models/ and
# point the settings at them:
#
#   DATASET3_MODEL_PATH=models/facial_concerns_efficientnet.keras
#   FACIAL_MODEL_METADATA_PATH=models/facial_concerns_metadata.json
#
# The metadata JSON supplies classes, per-class thresholds, image size
# and model version. Without it, the built-in values above are used
# (they belong to the original EfficientNetB0 artifact).

import json  # noqa: E402
import logging  # noqa: E402

_logger = logging.getLogger("skyntri.models")


@lru_cache(maxsize=1)
def facial_model_config() -> dict[str, Any]:
    default = {
        "classes": list(DATASET3_CLASSES),
        "thresholds": dict(DATASET3_THRESHOLDS),
        "image_size": IMAGE_SIZE[0],
        "model_version": settings.facial_model_version,
        "output": "sigmoid",
        "abstain_below": 0.0,
        "face_crop": False,
        "face_margin": 0.35,
        "tta": False,
        "display_names": {},
        "source": "built-in",
    }

    meta_path = Path(settings.facial_model_metadata)
    if not meta_path.is_file():
        return default

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        classes = [str(c) for c in meta["classes"]]
        thresholds = {c: float(meta["thresholds"][c]) for c in classes}
        size = int(meta.get("image_size", IMAGE_SIZE[0]))
        if not classes or not (32 <= size <= 1024):
            raise ValueError("invalid classes or image_size")
        if not all(0.0 < t < 1.0 for t in thresholds.values()):
            raise ValueError("thresholds must be between 0 and 1")
    except Exception as exc:
        raise ValueError(f"Invalid facial model metadata file: {exc}") from exc

    unknown = [c for c in classes if c not in CONDITION_RECOMMENDATIONS and c != "Normal Skin"]
    if unknown:
        _logger.warning(
            "facial_model_unknown_classes",
            extra={"event": "facial_model_unknown_classes", "classes": unknown},
        )

    face = meta.get("face_crop") or {}
    return {
        "classes": classes,
        "thresholds": thresholds,
        "image_size": size,
        "model_version": str(meta.get("model_version") or settings.facial_model_version),
        "output": str(meta.get("output", "sigmoid")).split()[0].lower(),
        "abstain_below": float(meta.get("abstain_below", 0.0) or 0.0),
        "face_crop": bool(face.get("enabled", False)) if isinstance(face, dict) else bool(face),
        "face_margin": float(face.get("margin", 0.35)) if isinstance(face, dict) else 0.35,
        "tta": bool(meta.get("tta", False)),
        "display_names": dict(meta.get("display_names") or {}),
        "source": meta_path.name,
    }


# ============================================================
# Inference concurrency (SEC-UP-007)
# ============================================================

class InferenceBusyError(RuntimeError):
    """Raised when too many inferences are already running."""


_inference_slots = threading.BoundedSemaphore(
    max(1, int(settings.max_concurrent_inference))
)


def model_loaded() -> bool:
    return load_dataset3_model.cache_info().currsize > 0


def model_artifact_available() -> bool:
    return Path(settings.dataset3_model).is_file()


# ============================================================
# Model loading
# ============================================================

@lru_cache(maxsize=1)
def load_dataset3_model() -> tf.keras.Model:
    """
    Load the final Dataset 3 EfficientNetB0 model once and cache it.

    The final model was trained using:
        EfficientNetB0
        + Weighted Focal Loss
        + Fine-Tuning

    compile=False is intentional because inference does not require
    the training optimizer or custom weighted focal loss.
    """
    model_path = Path(settings.dataset3_model)

    if not model_path.exists():
        raise FileNotFoundError(
            f"Dataset 3 EfficientNetB0 model was not found at: "
            f"{model_path}"
        )

    model = tf.keras.models.load_model(
        model_path,
        compile=False,
    )

    # --------------------------------------------------------
    # Basic output validation
    # --------------------------------------------------------
    output_shape = model.output_shape

    if not output_shape:
        raise ValueError(
            "Dataset 3 EfficientNetB0 model has no output shape."
        )

    try:
        output_count = int(output_shape[-1])
    except (TypeError, ValueError):
        raise ValueError(
            "Could not determine Dataset 3 model output size."
        )

    expected = len(facial_model_config()["classes"])

    if output_count != expected:
        raise ValueError(
            "Facial model output mismatch: "
            f"expected {expected}, "
            f"got {output_count}."
        )

    return model


# ============================================================
# Image preprocessing
# ============================================================

def preprocess_image(image_path: str | Path) -> np.ndarray:
    """
    Prepare an image exactly like the training notebook:
    RGB -> optional face crop -> bilinear resize -> float32 0..255.
    With TTA enabled in the metadata, a horizontally flipped copy is added
    and predictions are averaged.
    """
    config = facial_model_config()
    return prepare_batch(
        image_path,
        config["image_size"],
        face_crop=config["face_crop"],
        face_margin=config["face_margin"],
        tta=config["tta"],
    )


# ============================================================
# Dataset 3 inference
# ============================================================

def predict_dataset3(
    image_array: np.ndarray,
) -> dict[str, Any]:
    """
    Run Dataset 3 multi-label classification using EfficientNetB0.

    Each condition has its own optimized validation threshold.
    """
    model = load_dataset3_model()

    if not _inference_slots.acquire(
        timeout=max(0.1, float(settings.inference_queue_timeout_seconds))
    ):
        raise InferenceBusyError(
            "The analysis service is busy. Please try again shortly."
        )

    try:
        prediction = model.predict(
            image_array,
            verbose=0,
        )
    finally:
        _inference_slots.release()

    prediction_array = np.asarray(prediction, dtype=np.float64)

    if prediction_array.size == 0:
        raise ValueError(
            "Dataset 3 EfficientNetB0 model returned an empty prediction."
        )

    # Average test-time-augmentation copies (batch axis).
    if prediction_array.ndim == 2:
        prediction_array = prediction_array.mean(axis=0)

    flat_prediction = prediction_array.reshape(-1)

    config = facial_model_config()
    classes = config["classes"]

    if len(flat_prediction) < len(classes):
        raise ValueError(
            "Dataset 3 EfficientNetB0 model returned fewer outputs "
            "than expected."
        )

    probabilities: dict[str, dict[str, float | bool]] = {}
    detected_conditions: list[str] = []

    if float(np.max(flat_prediction[: len(classes)])) < config["abstain_below"]:
        # Softmax models: the top class is not confident enough -> abstain.
        return {"conditions": [], "probabilities": {}, "abstained": True}

    for index, condition in enumerate(classes):

        probability = _clip_probability(
            flat_prediction[index]
        )

        threshold = config["thresholds"][condition]

        detected = probability >= threshold

        probabilities[condition] = {
            "probability": probability,
            "threshold": threshold,
            "detected": detected,
        }

        if detected:
            detected_conditions.append(condition)

    # Softmax models: the most likely class is always reported (it already
    # passed the abstain_below check); other classes only above their threshold.
    if config["output"] == "softmax" and classes:
        top = classes[int(np.argmax(flat_prediction[: len(classes)]))]
        if top not in detected_conditions:
            probabilities[top]["detected"] = True
            detected_conditions = [top] + detected_conditions
        else:
            detected_conditions = [top] + [c for c in detected_conditions if c != top]
        # Report at most the 3 most likely concerns, strongest first.
        detected_conditions = [detected_conditions[0]] + sorted(
            detected_conditions[1:], key=lambda c: -probabilities[c]["probability"]
        )[:2]

    return {
        "conditions": detected_conditions,
        "probabilities": probabilities,
    }


# ============================================================
# Condition filtering
# ============================================================

def get_detected_conditions(
    dataset3_result: dict[str, Any],
) -> list[str]:
    """
    Return detected Dataset 3 conditions.

    Normal Skin is not treated as a skin problem and therefore is
    excluded from the recommendation list.
    """
    conditions: list[str] = []

    for condition in dataset3_result.get("conditions", []):

        if condition not in facial_model_config()["classes"]:
            continue

        if condition == "Normal Skin":
            continue

        conditions.append(condition)

    return _unique_preserve_order(conditions)


# ============================================================
# Severity estimation
# ============================================================

def _dataset3_severity_evidence(
    dataset3_result: dict[str, Any],
) -> tuple[int, int, list[float]]:
    """
    Calculate Dataset 3 severity evidence.

    This remains an AI-visible-pattern heuristic, not a medical
    severity classification.

    Returns:
        high_count:
            detected non-normal conditions with probability >= 0.85

        moderate_count:
            detected non-normal conditions with probability >= 0.60

        detected_probabilities:
            probabilities of detected non-normal conditions
    """
    high_count = 0
    moderate_count = 0
    detected_probabilities: list[float] = []

    probabilities = dataset3_result.get(
        "probabilities",
        {},
    )

    for condition in facial_model_config()["classes"]:

        if condition == "Normal Skin":
            continue

        item = probabilities.get(condition)

        if not isinstance(item, dict):
            continue

        probability = _clip_probability(
            item.get("probability", 0.0)
        )

        detected = bool(
            item.get("detected", False)
        )

        if not detected:
            continue

        detected_probabilities.append(probability)

        if probability >= 0.85:
            high_count += 1

        if probability >= 0.60:
            moderate_count += 1

    return (
        high_count,
        moderate_count,
        detected_probabilities,
    )


def calculate_severity(
    dataset3_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Estimate AI-visible-pattern severity using Dataset 3 only.

    This is deliberately a heuristic visual-pattern level.
    It is NOT a medical disease severity score.
    """
    detected_conditions = get_detected_conditions(
        dataset3_result
    )

    condition_count = len(detected_conditions)

    (
        high_count,
        moderate_count,
        detected_probabilities,
    ) = _dataset3_severity_evidence(
        dataset3_result
    )

    # --------------------------------------------------------
    # Severity rules
    # --------------------------------------------------------
    #
    # High:
    #   Multiple strong signals OR many concurrent patterns.
    #
    # Moderate:
    #   Multiple detected patterns OR one strong signal OR
    #   several moderate signals.
    #
    # Low:
    #   Limited detected evidence.
    #
    # This is an AI-estimated visual-pattern level, NOT medical
    # disease severity.
    # --------------------------------------------------------

    if (
        high_count >= 3
        or (
            condition_count >= 5
            and moderate_count >= 4
        )
    ):
        severity = "High"

    elif (
        condition_count >= 2
        or high_count >= 1
        or moderate_count >= 2
    ):
        severity = "Moderate"

    else:
        severity = "Low"

    if severity == "High":

        explanation = (
            "Multiple strong AI signals or several concurrent visible "
            "skin-pattern signals were detected."
        )

    elif severity == "Moderate":

        explanation = (
            "More than one visible skin pattern or meaningful AI "
            "confidence evidence was detected."
        )

    else:

        explanation = (
            "Limited AI-visible skin-pattern evidence was detected."
        )

    return {
        "level": severity,
        "explanation": explanation,
        "condition_count": condition_count,
        "high_evidence_count": high_count,
        "moderate_evidence_count": moderate_count,
        "detected_probabilities": detected_probabilities,
    }


# ============================================================
# Confidence calculation
# ============================================================

def calculate_confidence(
    dataset3_result: dict[str, Any],
) -> float:
    """
    Calculate a representative confidence percentage for the
    existing SkinAnalysis database field.

    For a multi-label model there is no single class confidence,
    so the strongest detected condition is used.

    If no condition crosses its threshold, the highest model
    probability is used as a fallback.
    """
    probabilities = dataset3_result.get(
        "probabilities",
        {},
    )

    detected_probabilities: list[float] = []
    all_probabilities: list[float] = []

    for condition in facial_model_config()["classes"]:

        item = probabilities.get(condition)

        if not isinstance(item, dict):
            continue

        probability = _clip_probability(
            item.get("probability", 0.0)
        )

        all_probabilities.append(probability)

        if (
            condition != "Normal Skin"
            and bool(item.get("detected", False))
        ):
            detected_probabilities.append(probability)

    if detected_probabilities:

        confidence = max(
            detected_probabilities
        )

    elif all_probabilities:

        confidence = max(
            all_probabilities
        )

    else:

        confidence = 0.0

    return round(
        confidence * 100.0,
        2,
    )


# ============================================================
# Recommendation builder
# ============================================================

def build_recommendations(
    conditions: list[str],
) -> dict[str, list[str]]:
    """
    Build user-facing recommendations from Dataset 3 detected
    conditions.

    Recommendations are deduplicated while preserving order.
    """
    skincare = list(
        UNIVERSAL_SKINCARE
    )

    ingredients: list[str] = []

    sun_protection = list(
        UNIVERSAL_SUN_PROTECTION
    )

    lifestyle = list(
        UNIVERSAL_LIFESTYLE
    )

    avoid = list(
        UNIVERSAL_AVOID
    )

    for condition in conditions:

        recommendation = CONDITION_RECOMMENDATIONS.get(
            condition
        )

        if not recommendation:
            continue

        skincare.extend(
            recommendation.get(
                "skincare",
                [],
            )
        )

        ingredients.extend(
            recommendation.get(
                "ingredients",
                [],
            )
        )

        lifestyle.extend(
            recommendation.get(
                "lifestyle",
                [],
            )
        )

        avoid.extend(
            recommendation.get(
                "avoid",
                [],
            )
        )

    return {
        "skincare": _unique_preserve_order(
            skincare
        ),
        "ingredients": _unique_preserve_order(
            ingredients
        ),
        "sun_protection": _unique_preserve_order(
            sun_protection
        ),
        "lifestyle": _unique_preserve_order(
            lifestyle
        ),
        "avoid": _unique_preserve_order(
            avoid
        ),
    }


# ============================================================
# Main analysis pipeline
# ============================================================

def analyze_skin_image(
    image_path: str | Path,
) -> dict[str, Any]:
    """
    Complete Skyntri Dataset 3-only skin-analysis pipeline.

    Final model:
        EfficientNetB0
        + Weighted Focal Loss
        + Fine-Tuning

    Flow:

        image
          ↓
        RGB conversion
          ↓
        resize 224x224
          ↓
        EfficientNetB0 input
          ↓
        Dataset 3 inference
          ↓
        optimized thresholds
          ↓
        detected conditions
          ↓
        AI-estimated severity
          ↓
        recommendations
          ↓
        clean API-ready result
    """
    image_array = preprocess_image(
        image_path
    )

    dataset3_result = predict_dataset3(
        image_array
    )

    # --------------------------------------------------------
    # Safe abstention (SEC-ML-004): if no label - not even
    # "Normal Skin" - reaches its validated threshold, the model
    # has no confident answer for this image. Do not force one.
    # --------------------------------------------------------
    if not dataset3_result.get("conditions"):
        return {
            "status": "uncertain",
            "conditions": [],
            "model_version": facial_model_config()["model_version"],
            "_internal": {"dataset3": dataset3_result},
        }

    conditions_internal = get_detected_conditions(
        dataset3_result
    )

    severity_result = calculate_severity(
        dataset3_result
    )

    recommendations = build_recommendations(
        conditions_internal
    )

    confidence_score = calculate_confidence(
        dataset3_result
    )

    user_conditions = [
        _display_name(condition)
        for condition in conditions_internal
    ]

    # --------------------------------------------------------
    # Public/clean result
    #
    # Do NOT expose:
    # - model name
    # - thresholds
    # - raw probabilities
    # - internal severity evidence
    # --------------------------------------------------------

    result = {
        "status": "completed",
        "model_version": facial_model_config()["model_version"],
        "conditions": user_conditions,
        "recommendations": recommendations,
        "confidence_score": confidence_score,
        "severity_level": severity_result["level"],
        "disclaimer": DISCLAIMER,

        # Internal fields remain available for local debugging,
        # reports, or future backend functionality.
        "_internal": {
            "dataset3": dataset3_result,
            "severity": severity_result,
            "conditions_internal": conditions_internal,
        },
    }

    return result


# ============================================================
# Debug helper
# ============================================================

def debug_analyze_skin_image(
    image_path: str | Path,
) -> dict[str, Any]:
    """
    Developer/debug version of Dataset 3 skin analysis.

    This intentionally exposes model-level details for local
    development/testing.

    Do NOT use this as the normal frontend API response.
    """
    result = analyze_skin_image(
        image_path
    )

    internal = result.get(
        "_internal",
        {},
    )

    return {
        "conditions": result["conditions"],
        "confidence_score": result["confidence_score"],
        "severity_level": result["severity_level"],
        "severity_explanation": internal.get(
            "severity",
            {},
        ).get(
            "explanation",
            "",
        ),
        "recommendations": result["recommendations"],
        "disclaimer": result["disclaimer"],
        "dataset3": internal.get(
            "dataset3",
            {},
        ),
        "severity_evidence": internal.get(
            "severity",
            {},
        ),
    }