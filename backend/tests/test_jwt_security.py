from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User


def test_jwt_tampering_and_deactivated_account(
    tmp_path,
    monkeypatch,
):
    # ---------------------------------------------------------
    # Create isolated temporary database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_jwt_security.db"

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

    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )

    monkeypatch.setattr(
        "app.routers.auth._failed_attempts",
        {},
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "JWT Security User",
                    "email": "jwt-security@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            data = register_response.json()

            token = data["access_token"]
            user_id = data["user"]["id"]

            # -------------------------------------------------
            # 2. Valid JWT should work
            # -------------------------------------------------
            valid_response = client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

            assert valid_response.status_code == 200
            assert valid_response.json()["id"] == user_id

            # -------------------------------------------------
            # 3. Tamper with the JWT
            # -------------------------------------------------
            tampered_token = token[:-2] + "XX"

            tampered_response = client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {tampered_token}"
                },
            )

            assert tampered_response.status_code == 401

            # -------------------------------------------------
            # 4. Deactivate the user in the database
            # -------------------------------------------------
            db = TestSessionLocal()

            try:
                user = db.get(
                    User,
                    user_id,
                )

                assert user is not None

                user.is_active = False

                db.commit()

            finally:
                db.close()

            # -------------------------------------------------
            # 5. Same previously valid token must now fail
            # -------------------------------------------------
            deactivated_response = client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

            assert deactivated_response.status_code == 401

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()