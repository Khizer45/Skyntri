from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


def test_authentication_integration(tmp_path, monkeypatch):
    # ---------------------------------------------------------
    # Create an isolated temporary SQLite database for testing
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_auth.db"

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

    # Use the temporary test database instead of the real database
    app.dependency_overrides[get_db] = override_get_db

    # Prevent the application startup from modifying the real database
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )

    # Clear authentication lockout state before the test
    monkeypatch.setattr(
        "app.routers.auth._failed_attempts",
        {},
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register a new user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Integration Test User",
                    "email": "integration@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            register_data = register_response.json()

            assert "access_token" in register_data
            assert register_data["user"]["email"] == "integration@test.com"

            access_token = register_data["access_token"]

            # -------------------------------------------------
            # 2. Login with the registered account
            # -------------------------------------------------
            login_response = client.post(
                "/auth/login",
                json={
                    "email": "integration@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert login_response.status_code == 200

            login_data = login_response.json()

            assert "access_token" in login_data
            assert login_data["user"]["email"] == "integration@test.com"

            # -------------------------------------------------
            # 3. Access protected /auth/me endpoint
            # -------------------------------------------------
            me_response = client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
            )

            assert me_response.status_code == 200

            me_data = me_response.json()

            assert me_data["email"] == "integration@test.com"
            assert me_data["full_name"] == "Integration Test User"

            # -------------------------------------------------
            # 4. Verify incorrect password is rejected
            # -------------------------------------------------
            wrong_login_response = client.post(
                "/auth/login",
                json={
                    "email": "integration@test.com",
                    "password": "WrongPassword123!",
                },
            )

            assert wrong_login_response.status_code == 401

    finally:
        # Remove the database override after the test
        app.dependency_overrides.clear()

        # Dispose temporary database connection
        test_engine.dispose()