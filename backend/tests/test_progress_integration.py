from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.db.database import Base, get_db


def _create_test_image(color):
    """Create a valid JPEG image for the integration test."""
    image = Image.new(
        "RGB",
        (300, 300),
        color=color,
    )

    buffer = BytesIO()
    image.save(
        buffer,
        format="JPEG",
    )

    return buffer.getvalue()


def test_progress_tracking_integration(tmp_path, monkeypatch):
    # ---------------------------------------------------------
    # Create isolated temporary SQLite database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_progress.db"

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

    # Prevent startup from modifying the real database
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )


    # ---------------------------------------------------------
    # Use a temporary upload location for the progress router
    # ---------------------------------------------------------
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    # ---------------------------------------------------------
    # Replace upload saving only.
    #
    # The actual progress calculation service remains active.
    # ---------------------------------------------------------
    counter = {"value": 0}

    def fake_save_upload(file, subfolder):
        counter["value"] += 1

        filename = (
            f"progress-test-{counter['value']}.jpg"
        )

        destination = (
            tmp_path
            / subfolder
            / filename
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = file.file.read()

        destination.write_bytes(content)

        return (
            f"/uploads/{subfolder}/{filename}"
        )

    monkeypatch.setattr(
        "app.routers.progress.save_upload",
        fake_save_upload,
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register test user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Progress Integration User",
                    "email": "progress@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            access_token = (
                register_response.json()["access_token"]
            )

            auth_headers = {
                "Authorization": f"Bearer {access_token}"
            }

            # -------------------------------------------------
            # 2. Prepare valid before/after images
            # -------------------------------------------------
            before_image = _create_test_image(
                (220, 80, 80)
            )

            after_image = _create_test_image(
                (170, 140, 140)
            )

            # -------------------------------------------------
            # 3. Submit progress comparison
            # -------------------------------------------------
            response = client.post(
                "/progress",
                headers=auth_headers,
                files={
                    "before_image": (
                        "before.jpg",
                        before_image,
                        "image/jpeg",
                    ),
                    "after_image": (
                        "after.jpg",
                        after_image,
                        "image/jpeg",
                    ),
                },
            )

            # -------------------------------------------------
            # 4. Verify successful response
            # -------------------------------------------------
            assert response.status_code == 201

            data = response.json()

            assert "id" in data
            # Private images are returned as signed URLs.
            assert data["before_image_url"].startswith(
                "/files/progress/"
            )
            assert data["after_image_url"].startswith(
                "/files/progress/"
            )

            assert data["status"] in {
                "Improved",
                "Deteriorated",
                "No Significant Change",
            }

            assert isinstance(
                data["score"],
                (int, float),
            )

            assert 0 <= data["score"] <= 100

            assert isinstance(
                data["observations"],
                list,
            )

            assert len(data["observations"]) == 3

            # -------------------------------------------------
            # 5. Verify database persistence
            # -------------------------------------------------
            from app.db.models import ProgressCheck

            db = TestSessionLocal()

            try:
                saved_progress = (
                    db.query(ProgressCheck)
                    .filter(
                        ProgressCheck.id
                        == data["id"]
                    )
                    .first()
                )

                assert saved_progress is not None

                assert (
                    saved_progress.status
                    == data["status"]
                )

                assert (
                    float(saved_progress.score)
                    == float(data["score"])
                )

                assert (
                    saved_progress.user_id
                    == register_response.json()["user"]["id"]
                )

                assert saved_progress.observations_json

            finally:
                db.close()

            # -------------------------------------------------
            # 6. Verify progress history
            # -------------------------------------------------
            history_response = client.get(
                "/progress",
                headers=auth_headers,
            )

            assert history_response.status_code == 200

            history = history_response.json()

            assert len(history) == 1
            assert history[0]["id"] == data["id"]

            # -------------------------------------------------
            # 7. Verify progress summary
            # -------------------------------------------------
            summary_response = client.get(
                "/progress/summary",
                headers=auth_headers,
            )

            assert summary_response.status_code == 200

            summary = summary_response.json()

            assert summary["total_checks"] == 1

            assert summary["average_score"] == data["score"]

            assert len(summary["timeline"]) == 1

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()