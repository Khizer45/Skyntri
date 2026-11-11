from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture
def api(tmp_path, monkeypatch):
    """
    Isolated API: temporary SQLite database and temporary private upload
    directory. Yields (client, SessionLocal).
    """
    # Set TEST_DATABASE_URL (e.g. a throwaway PostgreSQL) to run these tests
    # against a real server; the default is a temporary SQLite file.
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if pg_url:
        engine = create_engine(pg_url)
        Base.metadata.drop_all(bind=engine)
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'test.db'}",
            connect_args={"check_same_thread": False},
        )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.main.initialize_database", lambda: None)
    # Model files are not in the repository; API tests use fakes for inference.
    monkeypatch.setattr("app.routers.analyses.model_artifact_available", lambda: True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    # Webhooks are delivered in the request thread so tests can assert on them.
    monkeypatch.setattr("app.services.automation.DELIVERY_MODE", "inline")

    try:
        with TestClient(app) as client:
            yield client, SessionLocal
    finally:
        app.dependency_overrides.clear()
        if pg_url:
            Base.metadata.drop_all(bind=engine)
        engine.dispose()


def register(client, email: str, password: str = "TestPassword123!", name: str = "Test User"):
    response = client.post(
        "/auth/register",
        json={"full_name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
