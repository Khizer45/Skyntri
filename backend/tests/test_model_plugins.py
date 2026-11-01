"""Plug-in points for retrained Model A and for Model B (disease screening)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from app.core.config import settings
from app.services import disease_screening, skin_analysis
from tests.conftest import register
from tests.helpers import make_skin_closeup, to_bytes


@pytest.fixture(autouse=True)
def _clear_caches():
    skin_analysis.facial_model_config.cache_clear()
    disease_screening.load_metadata.cache_clear()
    yield
    skin_analysis.facial_model_config.cache_clear()
    disease_screening.load_metadata.cache_clear()


def test_facial_metadata_overrides_classes_thresholds_and_size(tmp_path, monkeypatch):
    meta = tmp_path / "facial.json"
    classes = list(skin_analysis.DATASET3_CLASSES)
    meta.write_text(json.dumps({
        "classes": classes,
        "thresholds": {c: 0.5 for c in classes},
        "image_size": 300,
        "model_version": "facial-test-v9",
    }))
    monkeypatch.setattr(settings, "facial_model_metadata_path", str(meta))

    cfg = skin_analysis.facial_model_config()
    assert cfg["image_size"] == 300 and cfg["model_version"] == "facial-test-v9"
    assert cfg["thresholds"]["Acne"] == 0.5

    image = tmp_path / "x.jpg"
    make_skin_closeup().save(image)
    assert skin_analysis.preprocess_image(image).shape == (1, 300, 300, 3)


def test_facial_defaults_without_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "facial_model_metadata_path", str(tmp_path / "missing.json"))
    cfg = skin_analysis.facial_model_config()
    assert cfg["source"] == "built-in" and cfg["image_size"] == 224


def test_invalid_facial_metadata_is_rejected(tmp_path, monkeypatch):
    meta = tmp_path / "bad.json"
    meta.write_text(json.dumps({"classes": ["Acne"], "thresholds": {"Acne": 1.5}}))
    monkeypatch.setattr(settings, "facial_model_metadata_path", str(meta))
    with pytest.raises(ValueError):
        skin_analysis.facial_model_config()


META = {
    "classes": ["Eczema / dermatitis", "Psoriasis", "Suspicious lesion", "Other / not supported"],
    "referral_classes": ["Suspicious lesion"],
    "other_class": "Other / not supported",
    "referral_threshold": 0.10,
    "abstain_below": 0.50,
}


def test_disease_interpretation_is_safe():
    # Referral wins even when another class has the top score
    r = disease_screening.interpret(np.array([0.7, 0.05, 0.15, 0.10]), META)
    assert r["status"] == "referral" and r["referral"] is True

    # Low confidence -> abstain
    assert disease_screening.interpret(np.array([0.40, 0.35, 0.05, 0.20]), META)["status"] == "uncertain"

    # "Other" is never an all-clear
    other = disease_screening.interpret(np.array([0.1, 0.1, 0.05, 0.75]), META)
    assert other["conditions"] == [] and "not a medical all-clear" in other["summary"]

    # A pattern is phrased as "may be consistent with", not a diagnosis
    p = disease_screening.interpret(np.array([0.05, 0.85, 0.05, 0.05]), META)
    assert "may be consistent with Psoriasis" in p["conditions"][0]


def test_disease_track_requires_flag_and_files(api, tmp_path, monkeypatch):
    client, _ = api
    tracks = {t["id"]: t["available"] for t in client.get("/analyses/tracks").json()}
    assert tracks == {"facial_concerns": True, "disease_screening": False}

    # Files present but flag off -> still unavailable
    model, meta = tmp_path / "m.keras", tmp_path / "m.json"
    model.write_bytes(b"x")
    meta.write_text(json.dumps(META))
    monkeypatch.setattr(settings, "disease_model_path", str(model))
    monkeypatch.setattr(settings, "disease_model_metadata_path", str(meta))
    assert disease_screening.is_available() is False

    monkeypatch.setattr(settings, "disease_screening_enabled", True)
    assert disease_screening.is_available() is True


def test_disease_track_end_to_end_with_fake_model(api, tmp_path, monkeypatch):
    client, _ = api
    monkeypatch.setattr("app.services.disease_screening.is_available", lambda: True)
    monkeypatch.setattr(
        "app.routers.analyses.disease_screening.screen_image",
        lambda path: {
            **disease_screening.interpret(np.array([0.05, 0.05, 0.85, 0.05]), META),
            "model_version": "disease-test",
            "disclaimer": disease_screening.DISCLAIMER,
            "recommendations": {"lifestyle": disease_screening.GENERAL_CARE},
        },
    )
    monkeypatch.setattr(
        "app.routers.analyses.analyze_skin_image",
        lambda path: (_ for _ in ()).throw(AssertionError("Model A must not run for the disease track")),
    )
    headers = register(client, "disease@test.com")

    response = client.post(
        "/analyses/analyze",
        headers=headers,
        data={"track": "disease_screening"},
        files={"file": ("arm.jpg", to_bytes(make_skin_closeup()), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["analysis_track"] == "disease_screening"
    assert body["referral"] is True
    assert "cannot diagnose or rule out" in body["disclaimer"]
    assert body["recommendations"]["ingredients"] == []
