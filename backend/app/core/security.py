from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# REQ-6.2 / SEC-AUTH-005: passwords hashed with bcrypt (cost factor >= 12).
BCRYPT_ROUNDS = 12


# ============================================================
# Passwords
# ============================================================

def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    )
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


# A real bcrypt hash used to keep login timing similar when the account does
# not exist (reduces account enumeration through response time).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def dummy_verify_password(plain_password: str) -> None:
    verify_password(plain_password, _DUMMY_HASH)


# ============================================================
# JWT access tokens (SEC-AUTH-009)
# ============================================================

def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """REQ-6.3: session management via short-lived JWT access tokens."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """
    Return the subject (user id) of a valid access token, otherwise None.

    Signature, algorithm, expiry, not-before, issuer, audience and token
    type are all validated.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require_exp": True,
                "require_sub": True,
                "require_aud": True,
                "require_iss": True,
                "require_iat": True,
            },
        )
    except JWTError:
        return None

    if payload.get("typ") != "access":
        return None

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        return None

    return subject


# ============================================================
# Opaque single-use tokens (password reset)
# ============================================================

def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Only this SHA-256 digest is stored (SEC-AUTH-007)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ============================================================
# Signed URLs for private files (SEC-DATA-003)
# ============================================================

def _file_signature(path: str, expires: int) -> str:
    key = hashlib.sha256(
        ("skyntri-file-url:" + settings.secret_key).encode("utf-8")
    ).digest()
    message = f"{path}\n{expires}".encode("utf-8")
    digest = hmac.new(key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_file_path(path: str, ttl_seconds: int | None = None) -> tuple[int, str]:
    ttl = ttl_seconds or settings.signed_url_ttl_seconds
    expires = int(time.time()) + int(ttl)
    return expires, _file_signature(path, expires)


def verify_file_signature(path: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False

    expected = _file_signature(path, expires)
    return hmac.compare_digest(expected, signature or "")
