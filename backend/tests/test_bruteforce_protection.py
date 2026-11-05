

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


def test_brute_force_login_protection(
    tmp_path,
    monkeypatch,
):
    # ---------------------------------------------------------
    # Create isolated temporary database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_bruteforce.db"

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


    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Create test account
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Brute Force Test User",
                    "email": "bruteforce@test.com",
                    "password": "CorrectPassword123!",
                },
            )

            assert register_response.status_code == 201

            # -------------------------------------------------
            # 2. Make five incorrect login attempts
            # -------------------------------------------------
            for _ in range(5):
                response = client.post(
                    "/auth/login",
                    json={
                        "email": "bruteforce@test.com",
                        "password": "WrongPassword123!",
                    },
                )

                assert response.status_code == 401

            # -------------------------------------------------
            # 3. Sixth attempt should be blocked
            # -------------------------------------------------
            locked_response = client.post(
                "/auth/login",
                json={
                    "email": "bruteforce@test.com",
                    "password": "WrongPassword123!",
                },
            )

            assert locked_response.status_code == 429

            assert (
                "Too many failed login attempts"
                in locked_response.json()["detail"]
            )

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()