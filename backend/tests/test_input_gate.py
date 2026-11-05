"""ML-01: non-skin / poor-quality images must never receive condition labels."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.services.image_gate import GateResult, assess_image
from tests.conftest import register
from tests.helpers import make_document, make_screen, make_skin_closeup, to_bytes

TESTS_DIR = Path(__file__).resolve().parent


def _save(tmp_path, image: Image.Image, name: str) -> Path:
    path = tmp_path / name
    image.save(path, quality=92)
    return path


def test_skin_closeup_is_accepted(tmp_path):
    result = assess_image(_save(tmp_path, make_skin_closeup(), "skin.jpg"))
    assert result.status == "accepted", result


@pytest.mark.parametrize(
    "image, expected_code",
    [
        (make_document(), "not_skin_image"),
        (make_screen(), "not_skin_image"),
        (Image.new("RGB", (300, 300), (5, 5, 5)), "image_too_dark"),
        (Image.new("RGB", (300, 300), (252, 252, 252)), "image_overexposed"),
        (Image.new("RGB", (300, 300), (120, 175, 200)), "image_low_detail"),
        (make_skin_closeup(size=100), "image_too_small"),
    ],
)
def test_non_skin_and_poor_quality_images_are_rejected(tmp_path, image, expected_code):
    result = assess_image(_save(tmp_path, image, "x.jpg"))
    assert result.status == "rejected"
    assert result.reason_code == expected_code


def test_repository_sample_images_are_not_skin(tmp_path):
    # The old sample images (solid black / solid blue) used to receive labels.
    for name in ["test_input_image.jpg"]:
        assert not assess_image(TESTS_DIR / name).accepted
    assert not assess_image(TESTS_DIR.parent / "test_skin.jpg").accepted


def _boom(*_args, **_kwargs):
    raise AssertionError("The condition model must not run for rejected images")


@pytest.mark.parametrize("factory", [make_screen, make_document])
def test_analyze_endpoint_abstains_and_never_calls_model(api, monkeypatch, factory):
    client, SessionLocal = api
    monkeypatch.setattr("app.routers.analyses.analyze_skin_image", _boom)
    headers = register(client, "gate@test.com")

    response = client.post(
        "/analyses/analyze",
        headers=headers,
        files={"file": ("laptop.jpg", to_bytes(factory()), "image/jpeg")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "not_skin_image"
    assert "conditions" not in response.text
    assert client.get("/analyses", headers=headers).json() == []

    from app.core.config import settings

    stored = list((settings.upload_path / "analyses").glob("*"))
    assert stored == []  # rejected images are deleted


def test_disease_track_is_not_available_yet(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr("app.routers.analyses.analyze_skin_image", _boom)
    headers = register(client, "track@test.com")

    response = client.post(
        "/analyses/analyze",
        headers=headers,
        data={"track": "disease_screening"},
        files={"file": ("skin.jpg", to_bytes(make_skin_closeup()), "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "track_not_available"


def test_uncertain_model_output_abstains(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(
        "app.routers.analyses.assess_image",
        lambda path, track="facial_concerns": GateResult("accepted", "accepted", "ok"),
    )
    monkeypatch.setattr(
        "app.routers.analyses.analyze_skin_image",
        lambda path: {"status": "uncertain", "conditions": [], "model_version": "m"},
    )
    headers = register(client, "uncertain@test.com")

    response = client.post(
        "/analyses/analyze",
        headers=headers,
        files={"file": ("skin.jpg", to_bytes(make_skin_closeup()), "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "model_uncertain"
    assert client.get("/analyses", headers=headers).json() == []


def test_model_abstains_when_no_label_crosses_threshold(monkeypatch):
    import numpy as np

    from app.services import skin_analysis

    class FakeModel:
        def predict(self, *_args, **_kwargs):
            return np.zeros((1, 10), dtype=np.float32)

    monkeypatch.setattr(skin_analysis, "load_dataset3_model", lambda: FakeModel())
    monkeypatch.setattr(skin_analysis, "preprocess_image", lambda path: np.zeros((1, 224, 224, 3)))

    result = skin_analysis.analyze_skin_image("ignored.jpg")
    assert result["status"] == "uncertain"
    assert result["conditions"] == []
