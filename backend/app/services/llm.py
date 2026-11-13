"""
Optional language-model calls: the assistant's answers, the agents' texts
and the assistant's illustrations.

Every public function returns None (or a Reply with ok=False) when no
provider is configured or the call fails, so callers always have a local
fallback.

Two things about Gemini are handled here, in one place:

* Google retires models regularly. When the configured text model no longer
  exists (HTTP 404), the list of models this key may use is read and the
  newest "flash" model is used from then on. Without this, a retired model
  would silently switch the assistant back to its built-in answers.
  Image models are billed per image, so they are never replaced
  automatically; the connection test names the available ones instead.

* Newer models "think" before they answer, and those thinking tokens count
  against maxOutputTokens. A small limit can therefore end an answer in the
  middle or leave it empty. Requests ask for the wanted answer size plus a
  fixed allowance, and a cut-off answer is reported to the caller.
"""

from __future__ import annotations

import base64
import logging
import re
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote

from app.core.config import settings
from app.services import http_client

logger = logging.getLogger("skyntri.llm")

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_API = "https://api.openai.com/v1"

DEFAULT_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"

# Added to the wanted answer size so "thinking" does not eat the answer.
THINKING_ALLOWANCE_TOKENS = 4096
MAX_REPLACEMENT_TRIES = 3
_MODEL_LIST_TTL_SECONDS = 3600

_lock = threading.Lock()
_state: dict = {"models": None, "models_at": 0.0, "replacement": {}}


@dataclass
class Reply:
    """The outcome of one Gemini request."""

    ok: bool
    model: str                 # the model that was asked last
    configured: str            # the model named in the settings
    status: int | None = None  # HTTP status; None when no response arrived
    error: str = ""            # why it failed, in the provider's words when it gave any
    data: dict | None = None

    @property
    def replaced(self) -> bool:
        """True when the configured model was unavailable and another one answered."""
        return self.ok and self.model != self.configured


def reset() -> None:
    """Forget the cached model list and replacement (used by tests)."""
    with _lock:
        _state.update(models=None, models_at=0.0, replacement={})


# ============================================================
# What is switched on
# ============================================================

def text_available() -> bool:
    return bool(
        settings.llm_enabled
        and settings.llm_provider.strip().casefold() == "gemini"
        and settings.gemini_api_key.strip()
    )


def image_provider() -> str | None:
    if not settings.llm_image_enabled:
        return None
    provider = settings.llm_provider.strip().casefold()
    if provider == "gemini" and settings.gemini_api_key.strip():
        return "gemini"
    if provider == "openai" and settings.openai_api_key.strip():
        return "openai"
    # Fall back to whichever key exists.
    if settings.gemini_api_key.strip():
        return "gemini"
    if settings.openai_api_key.strip():
        return "openai"
    return None


def configured_model(kind: str = "text") -> str:
    if kind == "image":
        name = settings.gemini_image_model.strip() or DEFAULT_IMAGE_MODEL
    else:
        name = settings.gemini_model.strip() or DEFAULT_TEXT_MODEL
    return name.removeprefix("models/")


def output_limit(answer_tokens: int) -> int:
    """maxOutputTokens for an answer of about `answer_tokens` tokens."""
    return max(int(answer_tokens or 0), 64) + THINKING_ALLOWANCE_TOKENS


# ============================================================
# Gemini: requests
# ============================================================

def _headers() -> dict[str, str]:
    return {"x-goog-api-key": settings.gemini_api_key.strip()}


def hide_secrets(text: str) -> str:
    """Remove any configured key or password from a text."""
    for secret in (settings.gemini_api_key, settings.openai_api_key, settings.stripe_secret_key,
                   settings.stripe_webhook_secret, settings.paypal_client_secret, settings.smtp_password):
        if secret and secret.strip():
            text = text.replace(secret.strip(), "[key]")
    return text


def clean_error(text: str) -> str:
    """A provider message that is safe to log and to show to an administrator."""
    text = hide_secrets(" ".join(str(text or "").split()))
    # Providers sometimes echo a shortened key ("sk-proj-****abcd").
    text = re.sub(r"\b(?:(?:sk|rk|pk|whsec)[-_]|AIza)[-_A-Za-z0-9*.]{6,}", "[key]", text)
    return text[:300]


def provider_error(response: http_client.HttpResponse) -> str:
    try:
        error = response.json().get("error")
    except http_client.HttpError:
        error = None
    message = error.get("message") if isinstance(error, dict) else error
    return clean_error(message or "") or f"HTTP {response.status}"


def _post(model: str, configured: str, body: dict, timeout: float) -> Reply:
    url = f"{GEMINI_MODELS_URL}/{quote(model, safe='')}:generateContent"
    try:
        response = http_client.send("POST", url, headers=_headers(), json_body=body, timeout=timeout)
    except http_client.HttpError:
        return Reply(False, model, configured, None, "Google could not be reached.")

    if not response.ok:
        return Reply(False, model, configured, response.status, provider_error(response))
    try:
        return Reply(True, model, configured, response.status, "", response.json())
    except http_client.HttpError:
        return Reply(False, model, configured, response.status, "Google's answer could not be read.")


def available_models(force: bool = False) -> list[dict] | None:
    """Models this API key may use (cached for an hour). None when the list cannot be read."""
    with _lock:
        fresh = time.time() - _state["models_at"] < _MODEL_LIST_TTL_SECONDS
        if _state["models"] is not None and fresh and not force:
            return _state["models"]

    models: list[dict] = []
    token = ""
    try:
        for _ in range(5):
            url = f"{GEMINI_MODELS_URL}?pageSize=1000" + (f"&pageToken={quote(token, safe='')}" if token else "")
            response = http_client.send("GET", url, headers=_headers(), timeout=15)
            if not response.ok:
                logger.warning("gemini_model_list_failed", extra={
                    "event": "gemini_model_list_failed", "status": response.status,
                    "reason": provider_error(response)})
                return None
            data = response.json()
            models.extend(m for m in data.get("models") or [] if isinstance(m, dict))
            token = str(data.get("nextPageToken") or "")
            if not token:
                break
    except http_client.HttpError:
        return None

    with _lock:
        _state.update(models=models, models_at=time.time())
    return models


def _generates_content(model: dict) -> bool:
    methods = model.get("supportedGenerationMethods") or model.get("supportedActions") or []
    return "generateContent" in methods


def _short_name(model: dict) -> str:
    return str(model.get("name") or "").removeprefix("models/")


def _newest_first(version: str) -> tuple[int, ...]:
    """Sort key that puts 3.8 before 3 and 3 before 2.5."""
    numbers = [int(n) for n in version.split(".")] if version else []
    return tuple(-n for n in (numbers + [0, 0, 0])[:3])


# Best first: a released "flash" model, Google's own alias for the newest one,
# the cheaper "lite" tier, then previews. "pro" models are never chosen: they
# cost more and often have no free quota.
_TEXT_PATTERNS = (
    re.compile(r"^gemini-(\d+(?:\.\d+)*)-flash(?:-\d{3})?$"),
    re.compile(r"^gemini-flash-latest$"),
    re.compile(r"^gemini-(\d+(?:\.\d+)*)-flash-lite(?:-\d{3})?$"),
    re.compile(r"^gemini-flash-lite-latest$"),
    re.compile(r"^gemini-(\d+(?:\.\d+)*)-flash-preview(?:-\d{2}-\d{2,4})?$"),
)
_IMAGE_NAME = re.compile(r"(?:^|-)image(?:-|$)|nano-banana")


def text_candidates(models: list[dict]) -> list[str]:
    """Text models to try when the configured one is gone, best first."""
    ranked = []
    for model in models:
        name = _short_name(model)
        if not _generates_content(model):
            continue
        for tier, pattern in enumerate(_TEXT_PATTERNS):
            match = pattern.match(name)
            if match:
                ranked.append((tier, _newest_first(match.group(1) if match.groups() else ""), name))
                break
    ranked.sort()
    # The best model of every kind first, so a few tries cover different
    # kinds (their quotas are counted separately).
    leaders, rest, seen = [], [], set()
    for tier, _, name in ranked:
        (rest if tier in seen else leaders).append(name)
        seen.add(tier)
    return leaders + rest


def image_models(models: list[dict]) -> list[str]:
    """Names of the image-generating models in a model list."""
    return sorted(
        name for name in (_short_name(m) for m in models if _generates_content(m))
        if name.startswith("gemini-") and _IMAGE_NAME.search(name)
    )


def ask_gemini(body: dict, *, kind: str = "text", timeout: float = 30) -> Reply:
    """
    Send one generateContent request.

    For text, a model that no longer exists is replaced by an available one
    and the choice is remembered until the server restarts.
    """
    configured = configured_model(kind)
    with _lock:
        model = _state["replacement"].get((kind, configured), configured)

    reply = _post(model, configured, body, timeout)
    if reply.status != 404 or kind != "text":
        if not reply.ok:
            logger.warning("gemini_request_failed", extra={
                "event": "gemini_request_failed", "model": model, "status": reply.status, "reason": reply.error})
        return reply

    with _lock:
        _state["replacement"].pop((kind, configured), None)

    tried = {model}
    for candidate in text_candidates(available_models(force=True) or []):
        if candidate in tried:
            continue
        if len(tried) > MAX_REPLACEMENT_TRIES:
            break
        tried.add(candidate)
        reply = _post(candidate, configured, body, min(timeout, 20))
        if reply.ok:
            with _lock:
                _state["replacement"][(kind, configured)] = candidate
            logger.warning("gemini_model_replaced", extra={
                "event": "gemini_model_replaced", "configured": configured, "model": candidate})
            return reply
        if reply.status not in (404, 429):
            break

    logger.warning("gemini_request_failed", extra={
        "event": "gemini_request_failed", "model": reply.model, "status": reply.status, "reason": reply.error})
    return reply


def extract_text(data: dict | None) -> tuple[str, bool]:
    """(text, cut_off) from a generateContent response."""
    try:
        candidate = (data or {}).get("candidates")[0]
        parts = (candidate.get("content") or {}).get("parts") or []
    except (AttributeError, IndexError, KeyError, TypeError):
        return "", False

    text = "".join(
        part["text"] for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str) and not part.get("thought")
    ).strip()
    return text, candidate.get("finishReason") == "MAX_TOKENS"


# ============================================================
# Text
# ============================================================

def generate_text(system: str, prompt: str, max_tokens: int = 500) -> str | None:
    """One short text for an agent. None when unavailable, failed or cut off."""
    if not text_available():
        return None
    reply = ask_gemini({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": output_limit(max_tokens)},
    })
    text, cut_off = extract_text(reply.data)
    # A text that stops in the middle must not be published.
    return text if text and not cut_off else None


# ============================================================
# Images
# ============================================================

def generate_image(prompt: str) -> bytes | None:
    """Return PNG/JPEG bytes of an illustration, or None."""
    provider = image_provider()
    try:
        if provider == "gemini":
            reply = ask_gemini(
                {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE"]},
                },
                kind="image", timeout=90,
            )
            if not reply.ok:
                return None
            for part in reply.data["candidates"][0]["content"]["parts"]:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            return None

        if provider == "openai":
            response = http_client.send(
                "POST",
                f"{OPENAI_API}/images/generations",
                headers={"Authorization": f"Bearer {settings.openai_api_key.strip()}"},
                json_body={"model": settings.openai_image_model.strip(), "prompt": prompt,
                           "size": "1024x1024", "n": 1},
                timeout=120,
            )
            if not response.ok:
                logger.warning("openai_image_failed", extra={
                    "event": "openai_image_failed", "status": response.status,
                    "reason": provider_error(response)})
                return None
            item = response.json()["data"][0]
            return base64.b64decode(item["b64_json"]) if item.get("b64_json") else None
    except (http_client.HttpError, AttributeError, KeyError, IndexError, TypeError, ValueError):
        return None
    return None
