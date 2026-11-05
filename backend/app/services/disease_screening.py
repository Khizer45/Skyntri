"""
Model B - skin disease screening SUPPORT (face and body).

Plug-in point for the model exported by
ml/notebooks/02_skin_disease_screening_efficientnet.ipynb:

    backend/models/skin_disease_efficientnet.keras   (DISEASE_MODEL_PATH)
    backend/models/skin_disease_metadata.json        (DISEASE_MODEL_METADATA_PATH)
    DISEASE_SCREENING_ENABLED=true                   (only after clinical review)

Safety rules (SEC-MED-001..007):
* Never diagnoses or rules out cancer. Referral classes are checked FIRST
  with a high-sensitivity threshold; reaching it always produces
  "see a doctor" guidance.
* Low confidence -> abstain ("uncertain").
* "Other / not supported" or no pattern is never phrased as an all-clear.
* No product recommendations are attached to disease results.
"""

from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings
from app.services.model_io import prepare_batch

DISCLAIMER = (
    "This is AI screening support, not a diagnosis. It cannot diagnose or rule "
    "out skin cancer or any other disease. If a spot is new, changing, bleeding, "
    "painful, itchy or worrying you, see a dermatologist or doctor even if this "
    "result does not flag it."
)

REFERRAL_MESSAGE = (
    "Some features in this photo may need a doctor's assessment. "
    "Please see a dermatologist or doctor soon."
)

GENERAL_CARE = [
    "Avoid scratching or picking the area.",
    "Do not apply steroid, bleaching or unverified creams without medical advice.",
    "Take a photo every few days in the same light to track changes.",
    "See a doctor promptly if the area spreads, bleeds, becomes painful, or you feel unwell.",
]

_lock = threading.Lock()


class DiseaseModelUnavailable(RuntimeError):
    pass


def model_files_present() -> bool:
    return Path(settings.disease_model).is_file() and Path(settings.disease_model_metadata).is_file()


def is_available() -> bool:
    """Model B is offered to users only when enabled AND both files exist."""
    return bool(settings.disease_screening_enabled) and model_files_present()


@lru_cache(maxsize=1)
def load_metadata() -> dict[str, Any]:
    meta = json.loads(Path(settings.disease_model_metadata).read_text(encoding="utf-8"))

    classes = [str(c) for c in meta["classes"]]
    referral = [str(c) for c in meta.get("referral_classes", [])]
    other = str(meta.get("other_class", "Other / not supported"))

    if not classes or any(c not in classes for c in referral):
        raise ValueError("Invalid disease model metadata (classes/referral_classes).")

    caution = [str(c) for c in meta.get("caution_classes", []) if str(c) in classes]

    return {
        "classes": classes,
        "referral_classes": referral,
        "caution_classes": caution,
        "tta": bool(meta.get("tta", False)),
        "display_names": dict(meta.get("display_names") or {}),
        "other_class": other,
        "referral_threshold": float(meta.get("referral_threshold", 0.05)),
        "abstain_below": float(meta.get("abstain_below", 0.5)),
        "image_size": int(meta.get("image_size", 224)),
        "model_version": str(meta.get("model_version", "skin-disease-unversioned")),
    }


@lru_cache(maxsize=1)
def load_model():
    if not model_files_present():
        raise DiseaseModelUnavailable("Disease screening model files are not installed.")

    import tensorflow as tf

    model = tf.keras.models.load_model(settings.disease_model, compile=False)
    expected = len(load_metadata()["classes"])
    if int(model.output_shape[-1]) != expected:
        raise ValueError(
            f"Disease model output mismatch: expected {expected}, got {model.output_shape[-1]}."
        )
    return model


def model_loaded() -> bool:
    return load_model.cache_info().currsize > 0


def _preprocess(path: Path, size: int, tta: bool = False) -> np.ndarray:
    # 0..255, EfficientNet rescales internally; optional flip for TTA
    return prepare_batch(path, size, face_crop=False, tta=tta)


def interpret(probs: np.ndarray, meta: dict[str, Any]) -> dict[str, Any]:
    """Turn softmax probabilities into a safe, user-facing result."""
    classes = meta["classes"]
    probs = np.clip(np.asarray(probs, dtype=np.float64).reshape(-1), 0.0, 1.0)
    top = int(np.argmax(probs))
    top_class = classes[top]
    confidence = round(float(probs[top]) * 100.0, 2)

    referral_hits = [
        c for c in meta["referral_classes"]
        if probs[classes.index(c)] >= meta["referral_threshold"]
    ]

    if referral_hits:
        return {
            "status": "referral",
            "conditions": [f"{c} - doctor's assessment recommended" for c in referral_hits],
            "summary": REFERRAL_MESSAGE,
            "referral": True,
            "confidence_score": confidence,
            "severity_level": "High",
        }

    if probs[top] < meta["abstain_below"]:
        return {"status": "uncertain"}

    shown = meta.get("display_names", {}).get(top_class, top_class)

    if top_class in meta.get("caution_classes", []):
        return {
            "status": "completed",
            "conditions": [f"{shown} - features of a skin lesion"],
            "summary": (
                f"The photo shows features often seen in {shown.lower()}. Only a doctor can "
                "confirm that a mole or spot is harmless. See a dermatologist if it is new, "
                "changing in size, shape or colour, bleeding, itchy or painful."
            ),
            "referral": False,
            "confidence_score": confidence,
            "severity_level": "Moderate",
        }

    if top_class == meta["other_class"]:
        return {
            "status": "completed",
            "conditions": [],
            "summary": (
                "No supported disease pattern was recognised. This is not a medical "
                "all-clear; see a doctor if you are concerned."
            ),
            "referral": False,
            "confidence_score": confidence,
            "severity_level": "Low",
        }

    return {
        "status": "completed",
        "conditions": [f"Features that may be consistent with {shown}"],
        "summary": (
            f"Some features may be consistent with {shown}. Only a clinician can "
            "confirm a diagnosis."
        ),
        "referral": False,
        "confidence_score": confidence,
        "severity_level": "Moderate",
    }


def screen_image(image_path: str | Path) -> dict[str, Any]:
    if not is_available():
        raise DiseaseModelUnavailable("Disease screening is not enabled.")

    meta = load_metadata()
    model = load_model()
    array = _preprocess(Path(image_path), meta["image_size"], meta.get("tta", False))

    with _lock:
        probs = np.asarray(model.predict(array, verbose=0), dtype=np.float32)
    probs = probs.mean(axis=0) if probs.ndim == 2 else probs.reshape(-1)

    result = interpret(probs, meta)
    result["model_version"] = meta["model_version"]
    if result["status"] != "uncertain":
        result["disclaimer"] = DISCLAIMER
        result["recommendations"] = {
            "skincare": [],
            "ingredients": [],
            "sun_protection": [],
            "lifestyle": GENERAL_CARE,
            "avoid": [],
        }
    return result
