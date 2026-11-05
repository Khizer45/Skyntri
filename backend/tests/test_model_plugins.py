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


def test_facial_track_reports_missing_model(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr("app.routers.analyses.model_artifact_available", lambda: False)
    tracks = {t["id"]: t for t in client.get("/analyses/tracks").json()}
    assert tracks["facial_concerns"]["available"] is False
    assert "not been installed" in tracks["facial_concerns"]["reason"]

    headers = register(client, "nomodel@test.com")
    response = client.post(
        "/analyses/analyze",
        headers=headers,
        files={"file": ("face.jpg", to_bytes(make_skin_closeup()), "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "model_not_installed"


def test_softmax_metadata_abstains_and_uses_tta(tmp_path, monkeypatch):
    classes = ["Acne", "Dark Spots", "Pores", "Wrinkles", "Normal Skin"]
    meta = tmp_path / "facial.json"
    meta.write_text(json.dumps({
        "classes": classes,
        "thresholds": {c: 0.35 for c in classes},
        "image_size": 64,
        "output": "softmax",
        "abstain_below": 0.5,
        "tta": True,
        "face_crop": {"enabled": True, "margin": 0.3},
        "model_version": "facial-softmax-test",
    }))
    monkeypatch.setattr(settings, "facial_model_metadata_path", str(meta))

    image = tmp_path / "x.jpg"
    make_skin_closeup().save(image)
    batch = skin_analysis.preprocess_image(image)
    assert batch.shape == (2, 64, 64, 3)  # original + flipped (TTA)
    assert np.allclose(batch[1], batch[0][:, ::-1, :])

    class Fake:
        def __init__(self, rows):
            self.rows = np.array(rows, dtype=np.float32)

        def predict(self, *_a, **_k):
            return self.rows

    # Confident: averaged top class 0.8 -> Acne detected
    monkeypatch.setattr(skin_analysis, "load_dataset3_model", lambda: Fake([[0.8, 0.1, 0.05, 0.03, 0.02]] * 2))
    result = skin_analysis.analyze_skin_image(image)
    assert result["status"] == "completed" and result["conditions"] == ["Acne"]
    assert result["model_version"] == "facial-softmax-test"

    # Not confident: top class 0.4 < abstain_below 0.5 -> uncertain
    monkeypatch.setattr(skin_analysis, "load_dataset3_model", lambda: Fake([[0.4, 0.3, 0.2, 0.05, 0.05]] * 2))
    assert skin_analysis.analyze_skin_image(image)["status"] == "uncertain"


def test_disease_caution_class_is_not_an_all_clear():
    meta = {**META, "classes": META["classes"] + ["Benign-appearing lesion"],
            "caution_classes": ["Benign-appearing lesion"]}
    r = disease_screening.interpret(np.array([0.02, 0.02, 0.05, 0.01, 0.90]), meta)
    assert r["status"] == "completed"
    assert "Only a doctor can confirm" in r["summary"]


def test_recommendations_drop_near_duplicate_tips():
    from app.services.skin_analysis import _unique_preserve_order, build_recommendations

    tips = [
        "Avoid harsh scrubbing.",
        "Harsh scrubbing",
        "Harsh physical scrubs",
        "Avoid picking or squeezing skin lesions.",
        "Very hot water",
    ]
    assert _unique_preserve_order(tips) == [
        "Avoid harsh scrubbing.",
        "Avoid picking or squeezing skin lesions.",
        "Very hot water",
    ]
    recs = build_recommendations(["Acne", "Blackheads & Whiteheads", "Dark Spots"])
    lowered = [tip.lower() for tip in recs["avoid"]]
    assert sum("scrub" in tip for tip in lowered) == 1
    assert len(recs["ingredients"]) == len(set(recs["ingredients"]))
