from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


def test_sql_injection_and_malicious_input_handling(
    tmp_path,
    monkeypatch,
):
    # ---------------------------------------------------------
    # Create isolated temporary database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_sql_injection.db"

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


    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. SQL-style malicious login input
            # -------------------------------------------------
            response = client.post(
                "/auth/login",
                json={
                    "email": "' OR '1'='1",
                    "password": "' OR '1'='1",
                },
            )

            # Request validation should reject malformed email input.
            assert response.status_code == 422

            # -------------------------------------------------
            # 2. Register a normal test user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "SQL Security User",
                    "email": "sql-security@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            token = register_response.json()["access_token"]

            # -------------------------------------------------
            # 3. Malicious analysis ID
            # -------------------------------------------------
            malicious_analysis_id = "' OR '1'='1' --"

            response = client.get(
                f"/analyses/{malicious_analysis_id}",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

            # The malicious value must not expose any record.
            assert response.status_code == 404

            # -------------------------------------------------
            # 4. Verify application is still functioning
            # -------------------------------------------------
            health_response = client.get("/health")

            assert health_response.status_code == 200
            assert health_response.json()["status"] == "ok"

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()