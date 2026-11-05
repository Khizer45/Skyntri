from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db.models import Ingredient


def test_ingredient_scanner_integration(tmp_path, monkeypatch):
    # ---------------------------------------------------------
    # Create isolated temporary SQLite database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_ingredient_scan.db"

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

    # Prevent startup from using the real database
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )


    # ---------------------------------------------------------
    # Add test ingredients to the temporary database
    # ---------------------------------------------------------
    db = TestSessionLocal()

    try:
        db.add_all(
            [
                Ingredient(
                    name="Niacinamide",
                    inci_name="Niacinamide",
                    aliases_json="[]",
                    category="Active",
                    function="Skin conditioning",
                    uses_json='["Oil control", "Barrier support"]',
                    safety_status="Beneficial",
                    safety_score=5,
                    suitable_skin_types_json='["Oily", "Normal"]',
                    avoid_skin_types_json="[]",
                    when_to_use="AM or PM",
                    precautions="Use as directed.",
                ),
                Ingredient(
                    name="Hyaluronic Acid",
                    inci_name="Hyaluronic Acid",
                    aliases_json="[]",
                    category="Humectant",
                    function="Hydration",
                    uses_json='["Hydration"]',
                    safety_status="Beneficial",
                    safety_score=5,
                    suitable_skin_types_json='["All"]',
                    avoid_skin_types_json="[]",
                    when_to_use="AM or PM",
                    precautions="Use with moisturizer.",
                ),
            ]
        )

        db.commit()

    finally:
        db.close()

    # ---------------------------------------------------------
    # Replace file saving with a controlled test implementation
    # ---------------------------------------------------------
    def fake_save_upload(file, subfolder):
        return "/uploads/ingredients_scans/test-ingredient.jpg"

    monkeypatch.setattr(
        "app.routers.scans.save_upload",
        fake_save_upload,
    )

    # ---------------------------------------------------------
    # Simulate OCR output
    #
    # The real ingredient token extraction function will process
    # this OCR text.
    # ---------------------------------------------------------
    def fake_extract_text(image_path):
        return (
            "Ingredients: Niacinamide, "
            "Hyaluronic Acid"
        )

    monkeypatch.setattr(
        "app.routers.scans.extract_text",
        fake_extract_text,
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Ingredient Test User",
                    "email": "ingredient@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            access_token = (
                register_response.json()["access_token"]
            )

            # -------------------------------------------------
            # 2. Scan ingredient image
            # -------------------------------------------------
            response = client.post(
                "/scans/scan",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                files={
                    "image": (
                        "ingredients.jpg",
                        b"fake image content",
                        "image/jpeg",
                    )
                },
            )

            # -------------------------------------------------
            # 3. Verify successful API response
            # -------------------------------------------------
            assert response.status_code == 201

            data = response.json()

            assert "id" in data
            assert data["image_url"].startswith(
                "/files/ingredients_scans/test-ingredient.jpg?exp="
            )

            assert data["total_ingredients"] == 2
            assert data["beneficial_count"] == 2
            assert data["caution_count"] == 0
            assert data["safety_score"] == 5
            assert data["safety_label"] == "Very Good"

            # -------------------------------------------------
            # 4. Verify ingredient matching results
            # -------------------------------------------------
            matched_names = [
                item["name"]
                for item in data["matched_ingredients"]
            ]

            assert "Niacinamide" in matched_names
            assert "Hyaluronic Acid" in matched_names

            assert data["unmatched_ingredients"] == []

            # -------------------------------------------------
            # 5. Verify database persistence
            # -------------------------------------------------
            db = TestSessionLocal()

            try:
                from app.db.models import IngredientScan

                saved_scan = (
                    db.query(IngredientScan)
                    .filter(
                        IngredientScan.id == data["id"]
                    )
                    .first()
                )

                assert saved_scan is not None
                assert (
                    saved_scan.total_ingredients == 2
                )
                assert (
                    saved_scan.beneficial_count == 2
                )
                assert (
                    saved_scan.caution_count == 0
                )
                assert (
                    saved_scan.safety_score == 5
                )

            finally:
                db.close()

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()