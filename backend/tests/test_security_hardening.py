"""Tests for the production-readiness security fixes (SK-01 .. SK-13)."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core import config as config_module
from app.core.config import ConfigurationError, Settings, settings, validate_for_startup
from app.db.models import PasswordResetToken, RateLimitEvent, User
from tests.conftest import register

# ---------------------------------------------------------------------------
# SK-01  Contact messages are admin-only
# ---------------------------------------------------------------------------

CONTACT = {"name": "A", "email": "a@test.com", "subject": "Hi", "message": "Hello there"}


def test_contact_submission_is_public_but_listing_is_admin_only(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "admin_emails", "admin@test.com")

    submitted = client.post("/contact", json=CONTACT)
    assert submitted.status_code == 201
    body = submitted.json()
    assert "message" in body and "email" not in body  # nothing echoed back

    assert client.get("/contact").status_code == 401

    user = register(client, "user@test.com")
    assert client.get("/contact", headers=user).status_code == 403
    assert client.get(f"/contact/{body['id']}", headers=user).status_code == 403
    assert client.delete(f"/contact/{body['id']}", headers=user).status_code == 403

    admin = register(client, "admin@test.com")
    listing = client.get("/contact", headers=admin)
    assert listing.status_code == 200
    assert listing.json()[0]["message"] == "Hello there"

    assert client.delete(f"/contact/{body['id']}", headers=admin).status_code == 204
    assert client.get("/contact", headers=admin).json() == []


def test_contact_submission_is_rate_limited(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "contact_per_hour", 3)

    codes = [client.post("/contact", json=CONTACT).status_code for _ in range(4)]
    assert codes == [201, 201, 201, 429]


def test_role_cannot_be_set_by_client(api):
    client, SessionLocal = api
    response = client.post(
        "/auth/register",
        json={"full_name": "X", "email": "x@test.com", "password": "TestPassword123!", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "user"


# ---------------------------------------------------------------------------
# SK-02  Password reset
# ---------------------------------------------------------------------------

def _capture_reset_links(monkeypatch):
    links: list[str] = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda email, name, link: links.append(link),
    )
    return links


def test_forgot_password_never_returns_token_and_stores_only_hash(api, monkeypatch):
    client, SessionLocal = api
    links = _capture_reset_links(monkeypatch)
    register(client, "reset@test.com")

    known = client.post("/auth/forgot-password", json={"email": "reset@test.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert "token" not in known.text.lower()

    raw_token = links[0].split("token=")[1]
    with SessionLocal() as db:
        stored = db.query(PasswordResetToken).one()
        assert stored.token != raw_token
        assert len(stored.token) == 64  # sha256 hex


def test_reset_token_is_single_use(api, monkeypatch):
    client, _ = api
    links = _capture_reset_links(monkeypatch)
    register(client, "single@test.com")
    client.post("/auth/forgot-password", json={"email": "single@test.com"})
    token = links[0].split("token=")[1]

    first = client.post("/auth/reset-password", json={"token": token, "new_password": "NewPassword123!"})
    replay = client.post("/auth/reset-password", json={"token": token, "new_password": "Another123!!"})

    assert first.status_code == 200
    assert replay.status_code == 400

    login = client.post("/auth/login", json={"email": "single@test.com", "password": "NewPassword123!"})
    assert login.status_code == 200


def test_expired_and_superseded_reset_tokens_fail(api, monkeypatch):
    client, SessionLocal = api
    links = _capture_reset_links(monkeypatch)
    register(client, "expired@test.com")

    client.post("/auth/forgot-password", json={"email": "expired@test.com"})
    client.post("/auth/forgot-password", json={"email": "expired@test.com"})
    old_token = links[0].split("token=")[1]
    new_token = links[1].split("token=")[1]

    # Requesting a new link invalidates the previous one.
    assert client.post(
        "/auth/reset-password", json={"token": old_token, "new_password": "NewPassword123!"}
    ).status_code == 400

    with SessionLocal() as db:
        for row in db.query(PasswordResetToken).all():
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    assert client.post(
        "/auth/reset-password", json={"token": new_token, "new_password": "NewPassword123!"}
    ).status_code == 400


def test_password_reset_disabled_in_production_without_email(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "smtp_host", "")
    response = client.post("/auth/forgot-password", json={"email": "x@test.com"})
    assert response.status_code == 503
    assert "token" not in response.text.lower()


# ---------------------------------------------------------------------------
# SK-03  JWT secret and claims
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "secret",
    ["", "change-this-to-a-long-random-secret", "short", "a" * 64],
)
def test_production_refuses_weak_secrets(secret):
    cfg = Settings(_env_file=None, environment="production", secret_key=secret)
    with pytest.raises(ConfigurationError):
        validate_for_startup(cfg)


def test_production_accepts_strong_secret_and_rejects_wildcard_cors():
    strong = "Zq8!" + "x7Kp2vL9mN4bR6tY1wE3uI5oA8sD0fG" * 2
    ok = Settings(_env_file=None, environment="production", secret_key=strong, cors_origins="https://app.example.com")
    validate_for_startup(ok)

    bad = Settings(_env_file=None, environment="production", secret_key=strong, cors_origins="*")
    with pytest.raises(ConfigurationError):
        validate_for_startup(bad)


def test_development_replaces_placeholder_secret():
    cfg = Settings(_env_file=None, environment="development", secret_key="change-this-to-a-long-random-secret")
    warnings = validate_for_startup(cfg)
    assert warnings
    assert cfg.secret_key != "change-this-to-a-long-random-secret"
    assert len(cfg.secret_key) >= config_module.MIN_SECRET_LENGTH


def test_tokens_without_expected_claims_are_rejected(api):
    client, _ = api
    headers = register(client, "claims@test.com")
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    now = datetime.now(timezone.utc)
    base = {"sub": user_id, "exp": now + timedelta(minutes=5), "iat": now, "typ": "access",
            "iss": settings.jwt_issuer, "aud": settings.jwt_audience}

    def call(claims, key=None, alg=None):
        token = jwt.encode(claims, key or settings.secret_key, algorithm=alg or settings.algorithm)
        return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code

    assert call(base) == 200
    assert call({k: v for k, v in base.items() if k != "aud"}) == 401
    assert call({**base, "iss": "someone-else"}) == 401
    assert call({**base, "typ": "refresh"}) == 401
    assert call({**base, "exp": now - timedelta(seconds=5)}) == 401
    assert call(base, key="forged-secret-" * 4) == 401


# ---------------------------------------------------------------------------
# SK-04  Private files and cross-user access
# ---------------------------------------------------------------------------

def _seed_analysis(SessionLocal, email: str, image_url: str) -> str:
    from app.db.models import SkinAnalysis

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        analysis = SkinAnalysis(
            user_id=user.id, image_url=image_url, predicted_condition="Acne",
            confidence_score=80.0, severity_level="Low",
        )
        db.add(analysis)
        db.commit()
        return analysis.id


def test_uploads_are_not_publicly_served_and_signed_urls_are_owner_scoped(api):
    from tests.helpers import make_jpeg_bytes

    client, SessionLocal = api
    alice = register(client, "alice@test.com")
    bob = register(client, "bob@test.com")

    folder = settings.upload_path / "analyses"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "alice.jpg").write_bytes(make_jpeg_bytes())
    analysis_id = _seed_analysis(SessionLocal, "alice@test.com", "/uploads/analyses/alice.jpg")

    # Old public static path is gone.
    assert client.get("/uploads/analyses/alice.jpg").status_code == 404

    # Owner gets a signed URL that works.
    own = client.get(f"/analyses/{analysis_id}", headers=alice)
    assert own.status_code == 200
    signed = own.json()["image_url"]
    assert signed.startswith("/files/analyses/alice.jpg?exp=")
    assert client.get(signed).status_code == 200

    # Another user cannot read the record (IDOR) and gets no URL.
    assert client.get(f"/analyses/{analysis_id}", headers=bob).status_code == 404
    assert all(item["id"] != analysis_id for item in client.get("/analyses", headers=bob).json())

    # Unsigned, tampered, or path-swapped URLs fail.
    assert client.get("/files/analyses/alice.jpg").status_code == 422
    assert client.get(signed.replace("sig=", "sig=x")).status_code == 403
    assert client.get(signed.replace("alice.jpg", "other.jpg")).status_code == 403


def test_signed_urls_expire(api, monkeypatch):
    from app.services.uploads import signed_url
    from tests.helpers import make_jpeg_bytes

    client, _ = api
    folder = settings.upload_path / "analyses"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "x.jpg").write_bytes(make_jpeg_bytes())

    url = signed_url("/uploads/analyses/x.jpg")
    assert client.get(url).status_code == 200

    real_time = time.time
    monkeypatch.setattr("app.core.security.time.time", lambda: real_time() + settings.signed_url_ttl_seconds + 5)
    assert client.get(url).status_code == 403


def test_manual_analysis_cannot_reference_another_users_file(api):
    client, SessionLocal = api
    register(client, "owner@test.com")
    attacker = register(client, "attacker@test.com")
    _seed_analysis(SessionLocal, "owner@test.com", "/uploads/analyses/secret.jpg")

    response = client.post(
        "/analyses",
        headers=attacker,
        json={
            "image_url": "/uploads/analyses/secret.jpg",
            "predicted_condition": "Acne",
            "confidence_score": 50,
            "severity_level": "Low",
        },
    )
    assert response.status_code == 400


def test_cross_user_access_to_reports_progress_scans_is_blocked(api):
    client, SessionLocal = api
    register(client, "a@test.com")
    bob = register(client, "b@test.com")
    analysis_id = _seed_analysis(SessionLocal, "a@test.com", None)

    assert client.post("/reports/generate", headers=bob, json={"analysis_id": analysis_id}).status_code == 404
    assert client.get("/reports/does-not-exist/download", headers=bob).status_code == 404
    assert client.get("/progress/does-not-exist", headers=bob).status_code == 404
    assert client.get("/scans/does-not-exist", headers=bob).status_code == 404


def test_account_deletion_removes_private_files(api):
    from tests.helpers import make_jpeg_bytes

    client, SessionLocal = api
    headers = register(client, "delete@test.com")

    folder = settings.upload_path / "analyses"
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / "mine.jpg"
    file_path.write_bytes(make_jpeg_bytes())
    _seed_analysis(SessionLocal, "delete@test.com", "/uploads/analyses/mine.jpg")

    assert client.delete("/auth/account", headers=headers).status_code == 204
    assert not file_path.exists()


# ---------------------------------------------------------------------------
# SK-07  Shared (database-backed) login throttling
# ---------------------------------------------------------------------------

def test_login_failures_are_throttled_in_the_shared_database(api):
    client, SessionLocal = api
    register(client, "brute@test.com")

    wrong = {"email": "brute@test.com", "password": "WrongPassword!!"}
    codes = [client.post("/auth/login", json=wrong).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429

    # Even the correct password is throttled until the window passes.
    right = {"email": "brute@test.com", "password": "TestPassword123!"}
    assert client.post("/auth/login", json=right).status_code == 429

    with SessionLocal() as db:
        rows = db.query(RateLimitEvent).filter(RateLimitEvent.bucket == "login_fail").all()
        assert len(rows) == 5
        assert all("brute" not in row.key_hash for row in rows)  # keys are hashed

        # Simulate the window passing: no permanent lock-out.
        for row in rows:
            row.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

    assert client.post("/auth/login", json=right).status_code == 200


def test_unknown_email_and_wrong_password_look_the_same(api):
    client, _ = api
    register(client, "exists@test.com")
    a = client.post("/auth/login", json={"email": "exists@test.com", "password": "WrongPassword!!"})
    b = client.post("/auth/login", json={"email": "missing@test.com", "password": "WrongPassword!!"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


# ---------------------------------------------------------------------------
# SK-10 / SEC-APP-002 / SEC-APP-004
# ---------------------------------------------------------------------------

def test_liveness_and_readiness(api, monkeypatch):
    client, _ = api
    assert client.get("/health").json()["status"] == "ok"

    monkeypatch.setattr("app.services.skin_analysis.model_artifact_available", lambda: False)
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    body = ready.json()
    assert body["checks"]["facial_model"]["ok"] is False
    assert "/" not in str(body["checks"]["facial_model"].get("version", ""))  # no paths leaked


def test_security_headers_and_oversized_requests(api):
    client, _ = api
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in response.headers

    too_big = client.post(
        "/contact",
        content=b"x",
        headers={"content-length": str(settings.max_request_bytes + 1), "content-type": "application/json"},
    )
    assert too_big.status_code == 413


def test_validation_errors_do_not_echo_passwords(api):
    client, _ = api
    response = client.post(
        "/auth/register",
        json={"full_name": "", "email": "bad", "password": "SuperSecretValue123"},
    )
    assert response.status_code == 422
    assert "SuperSecretValue123" not in response.text
