"""
Live checks of the optional outside services (Admin -> Settings -> Connections).

"Key set" only says that a value is present in the environment. A test sends
one harmless request with that value and reports what the provider answered,
so a wrong key, a retired model or a missing setting is found by the
administrator and not by a patient.

No test charges a customer, creates anything at a provider or sends e-mail.
The assistant test asks the language model for one word, which is free on
Google's free plan and costs a fraction of a cent on a paid one. Keys are
never part of a result.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote

from app.core.config import settings
from app.services import email as email_service
from app.services import google_auth, http_client, llm, payments

logger = logging.getLogger("skyntri.connections")

WORKING = "working"
PROBLEM = "problem"
NOT_SET_UP = "not_set_up"

RESTART_NOTE = "Values in .env are read when the backend starts: restart it after a change."


@dataclass
class Result:
    state: str
    summary: str
    details: list[str] = field(default_factory=list)


def _bearer(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.strip()}"}


# ============================================================
# Assistant (language model)
# ============================================================

def _assistant() -> Result:
    if not settings.llm_enabled or not settings.gemini_api_key.strip():
        return Result(NOT_SET_UP, "Set LLM_ENABLED=true and GEMINI_API_KEY in .env.", [RESTART_NOTE])

    provider = settings.llm_provider.strip() or "gemini"
    if provider.casefold() != "gemini":
        return Result(PROBLEM, f"LLM_PROVIDER is {provider}. The assistant's answers need LLM_PROVIDER=gemini.")

    reply = llm.ask_gemini({
        "contents": [{"role": "user", "parts": [{"text": "Reply with the single word OK."}]}],
        "generationConfig": {"maxOutputTokens": llm.output_limit(16)},
    })
    text, _ = llm.extract_text(reply.data)

    if reply.ok and text:
        details = []
        if reply.replaced:
            details.append(
                f"GEMINI_MODEL is {reply.configured}, which Google no longer offers to this key. "
                f"{reply.model} is used instead. Set GEMINI_MODEL={reply.model} in .env to make that permanent."
            )
        return Result(WORKING, f"Working: the model {reply.model} answered.", details)

    if reply.ok:
        return Result(PROBLEM, f"The model {reply.model} returned an empty answer.",
                      ["Test again. If it stays empty, set GEMINI_MODEL to another model."])

    if reply.status is None:
        return Result(PROBLEM, "Google could not be reached from the server.",
                      ["Check the server's internet connection, then test again."])

    said = f"Google said: {reply.error}"
    if reply.status == 404:
        names = llm.text_candidates(llm.available_models() or [])[:5]
        hint = (f"Set GEMINI_MODEL to one of: {', '.join(names)}." if names
                else "No usable model was found for this key. Create a new key in Google AI Studio.")
        return Result(PROBLEM, f"The model {reply.model} is not available to this key.", [hint, said])
    if reply.status == 429:
        return Result(PROBLEM, f"Google refused the request: the quota for {reply.model} is used up, "
                               "or this model has no free quota.",
                      ["Wait a minute and test again, or set GEMINI_MODEL to another model.", said])
    if reply.status in (400, 401, 403):
        return Result(PROBLEM, "Google did not accept GEMINI_API_KEY.",
                      ["Copy the key again from Google AI Studio (aistudio.google.com).", said])
    return Result(PROBLEM, f"Google answered with an error (HTTP {reply.status}).", [said])


# ============================================================
# Assistant illustrations (billed per image)
# ============================================================

NO_IMAGE_NOTE = (
    "No image was made by this test, because every image is billed. Ask the assistant "
    "for an image to confirm that billing is switched on at the provider."
)


def _images() -> Result:
    provider = llm.image_provider()
    if provider is None:
        if not settings.llm_image_enabled:
            return Result(NOT_SET_UP, "Set LLM_IMAGE_ENABLED=true in .env. Every image is billed by the provider.",
                          [RESTART_NOTE])
        return Result(PROBLEM, "LLM_IMAGE_ENABLED is on, but neither GEMINI_API_KEY nor OPENAI_API_KEY is set.")

    if provider == "gemini":
        wanted = llm.configured_model("image")
        models = llm.available_models(force=True)
        if models is None:
            return Result(PROBLEM, "Google did not return its list of models.",
                          ["Check GEMINI_API_KEY and the server's internet connection."])
        names = llm.image_models(models)
        if wanted in names:
            return Result(WORKING, f"The key works and the image model {wanted} is available.", [NO_IMAGE_NOTE])
        hint = (f"Set GEMINI_IMAGE_MODEL to one of: {', '.join(names[:6])}." if names
                else "This key has no image models. Image generation needs a Google account with billing switched on.")
        return Result(PROBLEM, f"The image model {wanted} is not available to this key.", [hint])

    wanted = settings.openai_image_model.strip()
    headers = _bearer(settings.openai_api_key)
    try:
        response = http_client.send(
            "GET", f"{llm.OPENAI_API}/models/{quote(wanted, safe='')}", headers=headers, timeout=20)
        if response.ok:
            return Result(WORKING, f"The key works and the image model {wanted} is available.", [NO_IMAGE_NOTE])
        if response.status == 401:
            return Result(PROBLEM, "OpenAI did not accept OPENAI_API_KEY.", ["Copy the key again from platform.openai.com."])
        if response.status == 404:
            listing = http_client.send("GET", f"{llm.OPENAI_API}/models", headers=headers, timeout=20)
            names = sorted(
                str(m.get("id")) for m in (listing.json().get("data") or [] if listing.ok else [])
                if isinstance(m, dict) and "image" in str(m.get("id"))
            )
            hint = (f"Set OPENAI_IMAGE_MODEL to one of: {', '.join(names[:6])}." if names
                    else "This key has no image models.")
            return Result(PROBLEM, f"The image model {wanted} is not available to this key.", [hint])
        return Result(PROBLEM, f"OpenAI answered with an error (HTTP {response.status}).",
                      [f"OpenAI said: {llm.provider_error(response)}"])
    except http_client.HttpError:
        return Result(PROBLEM, "OpenAI could not be reached from the server.")


# ============================================================
# Sign in with Google
# ============================================================

def _google() -> Result:
    client_id = settings.google_client_id.strip()
    if not client_id:
        return Result(NOT_SET_UP, "Set GOOGLE_CLIENT_ID in .env.", [RESTART_NOTE])
    if not client_id.endswith(".apps.googleusercontent.com"):
        return Result(PROBLEM, "GOOGLE_CLIENT_ID does not look like a Google client ID.",
                      ["It ends with .apps.googleusercontent.com. The client secret is not needed."])
    try:
        google_auth.check_keys()
    except google_auth.GoogleAuthUnavailable:
        return Result(PROBLEM, "Google's signing keys could not be loaded from the server.",
                      ["Sign-in fails until the server can reach www.googleapis.com."])
    return Result(
        WORKING,
        "Google's signing keys were loaded and the client ID has the right form.",
        ["Whether this site's address is allowed for the client ID is only known after one real sign-in. "
         "If the Google button shows an error, add the site address under \"Authorised JavaScript origins\" "
         "in Google Cloud Console."],
    )


# ============================================================
# Payments
# ============================================================

def _stripe() -> Result:
    key = settings.stripe_secret_key.strip()
    if not key:
        return Result(NOT_SET_UP, "Set STRIPE_SECRET_KEY in .env.", [RESTART_NOTE])
    try:
        response = http_client.send(
            "GET", f"{payments.STRIPE_API}/checkout/sessions?limit=1", headers=_bearer(key), timeout=20)
    except http_client.HttpError:
        return Result(PROBLEM, "Stripe could not be reached from the server.")

    if response.status == 401:
        return Result(PROBLEM, "Stripe did not accept STRIPE_SECRET_KEY.",
                      ["Copy the secret key again. It starts with sk_test_ or sk_live_ "
                       "(the publishable key, pk_..., does not work here)."])
    if response.status == 403:
        return Result(PROBLEM, "The key is valid, but it may not use Stripe Checkout.",
                      ["A restricted key needs write access to Checkout Sessions."])
    if not response.ok:
        return Result(PROBLEM, f"Stripe answered with an error (HTTP {response.status}).",
                      [f"Stripe said: {llm.provider_error(response)}"])

    test_mode = key.startswith(("sk_test_", "rk_test_"))
    details = []
    if not settings.stripe_webhook_secret:
        details.append("STRIPE_WEBHOOK_SECRET is not set: a payment is confirmed only when the customer "
                       "returns to the site after paying.")
    return Result(
        WORKING,
        "Stripe accepted the key (test mode: no real card is charged)." if test_mode
        else "Stripe accepted the key (live mode: real cards are charged).",
        details,
    )


def _paypal() -> Result:
    if not settings.paypal_configured:
        return Result(NOT_SET_UP, "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env.", [RESTART_NOTE])

    mode = "live" if settings.paypal_mode.strip().lower() == "live" else "sandbox"
    try:
        response = payments.paypal_token_response()
        accepted = response.ok and bool(response.json().get("access_token"))
    except http_client.HttpError:
        return Result(PROBLEM, "PayPal could not be reached from the server.")

    if not accepted:
        return Result(
            PROBLEM,
            f"PayPal did not accept PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET for the {mode} environment.",
            [f"Sandbox and live have different keys. PAYPAL_MODE is {mode}."],
        )

    currency = settings.shop_currency
    target = settings.paypal_currency.strip().upper() or "USD"
    if payments.paypal_amount(100.0, currency) is None:
        return Result(
            PROBLEM,
            f"PayPal accepted the keys ({mode}), but it cannot charge {currency}.",
            [f"Set PAYPAL_EXCHANGE_RATE to the number of {currency} for one {target}. "
             "Until then PayPal is not offered at checkout."],
        )
    return Result(
        WORKING,
        "PayPal accepted the keys (sandbox: no real money moves)." if mode == "sandbox"
        else "PayPal accepted the keys (live: real payments are taken).",
    )


# ============================================================
# E-mail
# ============================================================

def _email() -> Result:
    if not settings.smtp_configured:
        return Result(NOT_SET_UP, "Set SMTP_HOST and SMTP_FROM in .env.", [RESTART_NOTE])

    where = f"{settings.smtp_host}:{settings.smtp_port}"
    try:
        with email_service.open_server() as server:
            server.noop()
    except smtplib.SMTPAuthenticationError:
        return Result(PROBLEM, "The mail server refused SMTP_USERNAME / SMTP_PASSWORD.",
                      ["Gmail needs an app password (myaccount.google.com/apppasswords), not the normal password."])
    except (OSError, smtplib.SMTPException) as exc:
        return Result(PROBLEM, f"The mail server {where} could not be used ({type(exc).__name__}).",
                      ["Check SMTP_HOST and SMTP_PORT. Port 587 uses STARTTLS, port 465 uses SSL."])

    summary = (f"The mail server {where} accepted the login." if settings.smtp_username
               else f"The mail server {where} accepted the connection.")
    return Result(WORKING, summary, ["No e-mail was sent by this test."])


# ============================================================
# Entry point
# ============================================================

TESTS: dict[str, Callable[[], Result]] = {
    "assistant_llm": _assistant,
    "assistant_images": _images,
    "google_sign_in": _google,
    "card_payments": _stripe,
    "paypal": _paypal,
    "email": _email,
}


def run(name: str) -> dict:
    """Run one test. Raises KeyError for an unknown name."""
    test = TESTS[name]
    try:
        result = test()
    except Exception:  # noqa: BLE001 - a broken test must not break the settings page
        logger.exception("connection_test_failed", extra={"event": "connection_test_failed", "connection": name})
        result = Result(PROBLEM, "The test itself failed. The server log has the details.")

    return {
        "name": name,
        "state": result.state,
        "summary": llm.hide_secrets(result.summary),
        "details": [llm.hide_secrets(line) for line in result.details],
        "tested_at": datetime.now(timezone.utc),
    }
