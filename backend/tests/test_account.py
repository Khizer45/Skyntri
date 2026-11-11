"""Account: phone number, e-mail change, Google sign-in, first password."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.db.models import User
from app.services import google_auth
from tests.conftest import register


def _google(monkeypatch, sub="g-123", email="pat@gmail.com", name="Pat Google"):
    monkeypatch.setattr(settings, "google_client_id", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        google_auth, "verify_id_token", lambda credential: {"sub": sub, "email": email, "name": name}
    )


CRED = {"credential": "x" * 40}


def test_phone_is_validated_and_saved(api):
    client, _ = api
    headers = register(client, "phone@test.com")

    assert client.put("/profile", json={"phone": "not a phone"}, headers=headers).status_code == 422
    saved = client.put("/profile", json={"phone": "+92 300 1234567"}, headers=headers).json()
    assert saved["phone"] == "+92 300 1234567"
    assert client.put("/profile", json={"phone": ""}, headers=headers).json()["phone"] is None


def test_change_email_needs_password_and_free_address(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    headers = register(client, "old@test.com")
    register(client, "taken@test.com")

    def change(new_email, password="TestPassword123!"):
        return client.post("/profile/email", json={"new_email": new_email, "current_password": password},
                           headers=headers)

    assert change("new@test.com", "wrong-password").status_code == 400
    assert change("taken@test.com").status_code == 400
    # An administrator address cannot be claimed through an e-mail change.
    assert change("boss@test.com").status_code == 400

    assert change("New@Test.com").json()["email"] == "new@test.com"
    login = client.post("/auth/login", json={"email": "new@test.com", "password": "TestPassword123!"})
    assert login.status_code == 200 and login.json()["user"]["role"] == "user"
    assert client.post("/auth/login", json={"email": "old@test.com", "password": "TestPassword123!"}).status_code == 401


def test_google_sign_in_disabled_without_client_id(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "google_client_id", "")
    assert client.post("/auth/google", json=CRED).status_code == 503
    assert client.get("/config").json()["google_client_id"] is None


def test_google_sign_in_creates_account_then_logs_in(api, monkeypatch):
    client, SessionLocal = api
    _google(monkeypatch)

    first = client.post("/auth/google", json=CRED)
    assert first.status_code == 200, first.text
    user = first.json()["user"]
    assert user["email"] == "pat@gmail.com" and user["google_linked"] and user["email_verified"]
    assert user["password_set"] is False

    second = client.post("/auth/google", json=CRED).json()["user"]
    assert second["id"] == user["id"]
    with SessionLocal() as db:
        assert db.query(User).count() == 1

    # A Google-only account chooses a first password, once.
    headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    assert client.post("/auth/change-password", json={"current_password": "x", "new_password": "NewPassword123!"},
                       headers=headers).status_code == 400
    assert client.post("/auth/set-password", json={"new_password": "NewPassword123!"}, headers=headers).status_code == 200
    assert client.post("/auth/set-password", json={"new_password": "Another123456!"}, headers=headers).status_code == 400
    assert client.post("/auth/login", json={"email": "pat@gmail.com", "password": "NewPassword123!"}).status_code == 200
    # Its address belongs to Google.
    assert client.post("/profile/email", json={"new_email": "x@test.com", "current_password": "NewPassword123!"},
                       headers=headers).status_code == 409


def test_google_link_discards_unverified_password(api, monkeypatch):
    """Someone who registered the address first must not keep access."""
    client, _ = api
    register(client, "pat@gmail.com", password="AttackerPassword1!")
    _google(monkeypatch)

    linked = client.post("/auth/google", json=CRED).json()["user"]
    assert linked["google_linked"] and linked["password_set"] is False
    stolen = client.post("/auth/login", json={"email": "pat@gmail.com", "password": "AttackerPassword1!"})
    assert stolen.status_code == 401


def test_google_rejects_bad_token_and_inactive_user(api, monkeypatch):
    client, SessionLocal = api
    _google(monkeypatch)
    assert client.post("/auth/google", json=CRED).status_code == 200
    with SessionLocal() as db:
        db.query(User).update({User.is_active: False})
        db.commit()
    assert client.post("/auth/google", json=CRED).status_code == 403

    def bad(_credential):
        raise google_auth.GoogleAuthError("bad")

    monkeypatch.setattr(google_auth, "verify_id_token", bad)
    assert client.post("/auth/google", json=CRED).status_code == 401


def test_verify_id_token_checks_signature_audience_and_email(monkeypatch):
    """Real RS256 verification against a locally generated key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose import jwk, jwt

    def keypair():
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        public_pem = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem, {**jwk.construct(public_pem, "RS256").to_dict(), "kid": "k1"}

    pem, public_jwk = keypair()
    other_pem, _ = keypair()
    monkeypatch.setattr(settings, "google_client_id", "my-client")
    monkeypatch.setattr(google_auth, "_load_keys", lambda force=False: {"k1": public_jwk})

    import time

    def token(key=pem, **overrides):
        claims = {"iss": "https://accounts.google.com", "aud": "my-client", "sub": "42", "email": "A@Gmail.com",
                  "email_verified": True, "name": "A", "exp": int(time.time()) + 300, **overrides}
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})

    assert google_auth.verify_id_token(token()) == {"sub": "42", "email": "a@gmail.com", "name": "A"}
    for bad in (token(aud="someone-else"), token(iss="https://evil.example"), token(email_verified=False),
                token(exp=int(time.time()) - 10), token(key=other_pem), "not-a-jwt"):
        with pytest.raises(google_auth.GoogleAuthError):
            google_auth.verify_id_token(bad)
    # A token "signed" with the shared-secret algorithm is refused outright.
    with pytest.raises(google_auth.GoogleAuthError):
        google_auth.verify_id_token(jwt.encode({"sub": "1"}, "secret", algorithm="HS256", headers={"kid": "k1"}))


def test_admin_can_switch_disease_screening(api, monkeypatch, tmp_path):
    client, _ = api
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    admin = register(client, "boss@test.com")
    user = register(client, "u@test.com")

    assert client.get("/admin/settings", headers=user).status_code == 403
    assert client.put("/admin/settings", json={"key": "disease_screening_enabled", "value": True},
                      headers=user).status_code == 403

    def disease_available():
        tracks = client.get("/analyses/tracks").json()
        return next(t for t in tracks if t["id"] == "disease_screening")["available"]

    # Cannot be switched on while the model files are missing.
    assert client.put("/admin/settings", json={"key": "disease_screening_enabled", "value": True},
                      headers=admin).status_code == 409

    model, meta = tmp_path / "d.keras", tmp_path / "d.json"
    model.write_bytes(b"x")
    meta.write_text("{}")
    monkeypatch.setattr(settings, "disease_model_path", str(model))
    monkeypatch.setattr(settings, "disease_model_metadata_path", str(meta))
    assert disease_available() is False

    on = client.put("/admin/settings", json={"key": "disease_screening_enabled", "value": True}, headers=admin)
    assert on.status_code == 200
    assert next(s for s in on.json()["settings"] if s["key"] == "disease_screening_enabled")["value"] is True
    assert disease_available() is True

    # The administrator's choice also wins over DISEASE_SCREENING_ENABLED=true.
    monkeypatch.setattr(settings, "disease_screening_enabled", True)
    client.put("/admin/settings", json={"key": "disease_screening_enabled", "value": False}, headers=admin)
    assert disease_available() is False

    assert client.put("/admin/settings", json={"key": "secret_key", "value": True}, headers=admin).status_code == 404
    actions = [e["action"] for e in client.get("/admin/audit", headers=admin).json()]
    assert actions.count("setting.changed") == 2
