from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


def test_security_authentication_and_user_isolation(
    tmp_path,
    monkeypatch,
):
    # ---------------------------------------------------------
    # Create isolated temporary database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_security.db"

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

    # Prevent real database initialization
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )

    # Clear login lockout state
    monkeypatch.setattr(
        "app.routers.auth._failed_attempts",
        {},
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Protected endpoint without token
            # -------------------------------------------------
            response = client.get("/auth/me")

            assert response.status_code == 401

            # -------------------------------------------------
            # 2. Protected endpoint with invalid token
            # -------------------------------------------------
            response = client.get(
                "/auth/me",
                headers={
                    "Authorization": "Bearer invalid-token"
                },
            )

            assert response.status_code == 401

            # -------------------------------------------------
            # 3. Create User A
            # -------------------------------------------------
            user_a_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Security User A",
                    "email": "security-a@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert user_a_response.status_code == 201

            user_a_data = user_a_response.json()

            token_a = user_a_data["access_token"]
            user_a_id = user_a_data["user"]["id"]

            # -------------------------------------------------
            # 4. Create User B
            # -------------------------------------------------
            user_b_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Security User B",
                    "email": "security-b@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert user_b_response.status_code == 201

            user_b_data = user_b_response.json()

            token_b = user_b_data["access_token"]
            user_b_id = user_b_data["user"]["id"]

            assert user_a_id != user_b_id

            # -------------------------------------------------
            # 5. Verify User A can access own account
            # -------------------------------------------------
            own_account_response = client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {token_a}"
                },
            )

            assert own_account_response.status_code == 200
            assert (
                own_account_response.json()["id"]
                == user_a_id
            )

            # -------------------------------------------------
            # 6. Create a skin analysis belonging to User A
            # -------------------------------------------------
            from app.db.models import SkinAnalysis

            db = TestSessionLocal()

            try:
                analysis = SkinAnalysis(
                    user_id=user_a_id,
                    image_url="/uploads/analyses/security-test.jpg",
                    predicted_condition="Acne",
                    confidence_score=90.0,
                    severity_level="Moderate",
                    explanation="Security integration test.",
                )

                db.add(analysis)
                db.commit()
                db.refresh(analysis)

                analysis_id = analysis.id

            finally:
                db.close()

            # -------------------------------------------------
            # 7. User A can access own analysis
            # -------------------------------------------------
            own_analysis_response = client.get(
                f"/analyses/{analysis_id}",
                headers={
                    "Authorization": f"Bearer {token_a}"
                },
            )

            assert own_analysis_response.status_code == 200

            assert (
                own_analysis_response.json()["id"]
                == analysis_id
            )

            # -------------------------------------------------
            # 8. User B must NOT access User A's analysis
            # -------------------------------------------------
            other_user_response = client.get(
                f"/analyses/{analysis_id}",
                headers={
                    "Authorization": f"Bearer {token_b}"
                },
            )

            assert other_user_response.status_code == 404

            # -------------------------------------------------
            # 9. User B history must not contain User A data
            # -------------------------------------------------
            user_b_history = client.get(
                "/analyses",
                headers={
                    "Authorization": f"Bearer {token_b}"
                },
            )

            assert user_b_history.status_code == 200
            assert user_b_history.json() == []

            # -------------------------------------------------
            # 10. User A history must contain own analysis
            # -------------------------------------------------
            user_a_history = client.get(
                "/analyses",
                headers={
                    "Authorization": f"Bearer {token_a}"
                },
            )

            assert user_a_history.status_code == 200

            history_data = user_a_history.json()

            assert len(history_data) == 1
            assert history_data[0]["id"] == analysis_id

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()