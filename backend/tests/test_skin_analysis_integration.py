from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.db.database import Base, get_db
from app.services.image_gate import GateResult
from tests.helpers import make_jpeg_bytes


def test_skin_analysis_integration(tmp_path, monkeypatch):
    # ---------------------------------------------------------
    # Create isolated temporary SQLite database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_skin_analysis.db"

    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Prevent startup from touching the real database
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )


    # ---------------------------------------------------------
    # Fake upload function
    #
    # The real endpoint will still call save_upload(),
    # but this test stores the file inside the temporary
    # test directory instead of the real uploads folder.
    # ---------------------------------------------------------
    monkeypatch.setattr("app.routers.analyses.model_artifact_available", lambda: True)

    # Private uploads go to a temporary directory for this test.
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    # The input gate is tested separately (tests/test_input_gate.py).
    # Here it is forced to "accepted" so the API -> service -> DB flow
    # can be tested with a controlled model result.
    monkeypatch.setattr(
        "app.routers.analyses.assess_image",
        lambda image_path, track="facial_concerns": GateResult(
            "accepted", "accepted", "Image accepted for analysis."
        ),
    )

    # ---------------------------------------------------------
    # Fake AI result
    #
    # The actual AI model is not loaded during this integration
    # test. We test the API -> analysis-service -> database flow
    # using a controlled service response.
    # ---------------------------------------------------------
    def fake_analyze_skin_image(image_path):
        assert Path(image_path).exists()

        return {
            "status": "completed",
            "model_version": "test-model",
            "conditions": [
                "Acne",
                "Oily Skin",
            ],
            "recommendations": {
                "skincare": [
                    "Use a gentle cleanser."
                ],
                "ingredients": [
                    "Salicylic acid"
                ],
                "sun_protection": [
                    "Use broad-spectrum SPF 30+ sunscreen."
                ],
                "lifestyle": [
                    "Keep a consistent skincare routine."
                ],
                "avoid": [
                    "Avoid picking or squeezing pimples."
                ],
            },
            "confidence_score": 91.5,
            "severity_level": "Moderate",
            "disclaimer": (
                "This result is an AI-estimated assessment of "
                "visible skin patterns, not a medical diagnosis."
            ),
        }

    monkeypatch.setattr(
        "app.routers.analyses.analyze_skin_image",
        fake_analyze_skin_image,
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Skin Analysis Test User",
                    "email": "skin-analysis@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            access_token = (
                register_response.json()["access_token"]
            )

            # -------------------------------------------------
            # 2. Upload an image to /analyses/analyze
            # -------------------------------------------------
            image_bytes = make_jpeg_bytes()

            response = client.post(
                "/analyses/analyze",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                files={
                    "file": (
                        "test_skin.jpg",
                        image_bytes,
                        "image/jpeg",
                    )
                },
            )

            # Endpoint should successfully create the analysis
            assert response.status_code == 201

            data = response.json()

            # -------------------------------------------------
            # 3. Verify API response
            # -------------------------------------------------
            assert "analysis_id" in data
            # Private images are returned as short-lived signed URLs.
            assert data["image_url"].startswith("/files/analyses/")
            assert "sig=" in data["image_url"]
            assert data["analysis_track"] == "facial_concerns"
            assert data["model_version"] == "test-model"

            image_response = client.get(data["image_url"])
            assert image_response.status_code == 200
            assert image_response.headers["content-type"] == "image/jpeg"
            assert data["conditions"] == [
                "Acne",
                "Oily Skin",
            ]
            assert data["confidence_score"] == 91.5
            assert data["severity_level"] == "Moderate"
            assert "disclaimer" in data

            # -------------------------------------------------
            # 4. Verify database persistence
            # -------------------------------------------------
            db = TestSessionLocal()

            try:
                from app.db.models import SkinAnalysis

                saved_analysis = (
                    db.query(SkinAnalysis)
                    .filter(
                        SkinAnalysis.id
                        == data["analysis_id"]
                    )
                    .first()
                )

                assert saved_analysis is not None
                assert (
                    saved_analysis.predicted_condition
                    == "Acne, Oily Skin"
                )
                assert (
                    saved_analysis.confidence_score
                    == 91.5
                )
                assert (
                    saved_analysis.severity_level
                    == "Moderate"
                )

            finally:
                db.close()

            # -------------------------------------------------
            # 5. Verify authenticated history contains result
            # -------------------------------------------------
            history_response = client.get(
                "/analyses",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
            )

            assert history_response.status_code == 200

            history = history_response.json()

            assert len(history) == 1
            assert history[0]["id"] == data["analysis_id"]

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()