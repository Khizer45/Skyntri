"""
Sign in with Google: verify the ID token the browser receives from Google
Identity Services.

The token is a JWT signed by Google. It is accepted only when the signature
matches one of Google's published keys, the audience is this application's
client ID, the issuer is Google, it has not expired and the e-mail address
is verified.
"""

from __future__ import annotations

import threading
import time

from jose import JWTError, jwt

from app.core.config import settings
from app.services import http_client

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_CERTS_TTL_SECONDS = 3600

_lock = threading.Lock()
_cache: dict = {"keys": {}, "fetched_at": 0.0}


class GoogleAuthError(Exception):
    """The Google credential was not accepted."""


class GoogleAuthUnavailable(Exception):
    """Google's signing keys could not be loaded."""


def _load_keys(force: bool = False) -> dict[str, dict]:
    with _lock:
        fresh = time.time() - _cache["fetched_at"] < _CERTS_TTL_SECONDS
        if _cache["keys"] and fresh and not force:
            return _cache["keys"]

        try:
            response = http_client.send("GET", GOOGLE_CERTS_URL, timeout=8)
        except http_client.HttpError as exc:
            raise GoogleAuthUnavailable("Google keys could not be loaded") from exc
        if not response.ok:
            raise GoogleAuthUnavailable("Google keys could not be loaded")

        keys = {k["kid"]: k for k in response.json().get("keys", []) if k.get("kid")}
        if not keys:
            raise GoogleAuthUnavailable("Google returned no signing keys")

        _cache.update(keys=keys, fetched_at=time.time())
        return keys


def check_keys() -> int:
    """Load Google's signing keys again and return how many there are. Raises GoogleAuthUnavailable."""
    return len(_load_keys(force=True))


def verify_id_token(credential: str) -> dict:
    """
    Return {"sub", "email", "name"} for a valid Google ID token.
    Raises GoogleAuthError for anything else.
    """
    if not settings.google_client_id:
        raise GoogleAuthUnavailable("Google sign-in is not configured")

    try:
        header = jwt.get_unverified_header(credential)
    except JWTError as exc:
        raise GoogleAuthError("Malformed credential") from exc

    if header.get("alg") != "RS256":
        raise GoogleAuthError("Unexpected signing algorithm")

    kid = header.get("kid")
    keys = _load_keys()
    if kid not in keys:
        # Google rotates keys; refresh once before giving up.
        keys = _load_keys(force=True)
    if kid not in keys:
        raise GoogleAuthError("Unknown signing key")

    try:
        claims = jwt.decode(
            credential,
            keys[kid],
            algorithms=["RS256"],
            audience=settings.google_client_id,
            options={"verify_at_hash": False, "require_exp": True, "require_sub": True},
        )
    except JWTError as exc:
        raise GoogleAuthError("Invalid credential") from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleAuthError("Unexpected issuer")

    email = str(claims.get("email") or "").strip().lower()
    if not email or claims.get("email_verified") not in (True, "true"):
        raise GoogleAuthError("The Google account has no verified e-mail address")

    return {
        "sub": str(claims["sub"]),
        "email": email,
        "name": str(claims.get("name") or "").strip()[:120],
    }
