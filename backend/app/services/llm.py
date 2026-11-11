"""
Optional language-model calls used by the agents and by the assistant's
illustrations. Every function returns None when no provider is configured
or the call fails, so callers always have a local fallback.
"""

from __future__ import annotations

import base64

from app.core.config import settings
from app.services import http_client

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


def text_available() -> bool:
    return bool(
        settings.llm_enabled
        and settings.llm_provider.strip().casefold() == "gemini"
        and settings.gemini_api_key.strip()
    )


def generate_text(system: str, prompt: str, max_tokens: int = 500) -> str | None:
    if not text_available():
        return None
    model = settings.gemini_model.strip() or "gemini-2.5-flash"
    try:
        response = http_client.send(
            "POST",
            f"{GEMINI_URL}{model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key.strip()},
            json_body={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
            timeout=30,
        )
        if not response.ok:
            return None
        parts = response.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except (http_client.HttpError, KeyError, IndexError, TypeError):
        return None


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


def generate_image(prompt: str) -> bytes | None:
    """Return PNG/JPEG bytes of an illustration, or None."""
    provider = image_provider()
    try:
        if provider == "gemini":
            response = http_client.send(
                "POST",
                f"{GEMINI_URL}{settings.gemini_image_model.strip()}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key.strip()},
                json_body={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE"]},
                },
                timeout=90,
            )
            if not response.ok:
                return None
            for part in response.json()["candidates"][0]["content"]["parts"]:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            return None

        if provider == "openai":
            response = http_client.send(
                "POST",
                OPENAI_IMAGES_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key.strip()}"},
                json_body={"model": settings.openai_image_model.strip(), "prompt": prompt,
                           "size": "1024x1024", "n": 1},
                timeout=120,
            )
            if not response.ok:
                return None
            item = response.json()["data"][0]
            return base64.b64decode(item["b64_json"]) if item.get("b64_json") else None
    except (http_client.HttpError, KeyError, IndexError, TypeError, ValueError):
        return None
    return None
