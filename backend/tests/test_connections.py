"""
The language-model client (retired models, cut-off answers) and the
connection tests in Admin -> Settings. Every provider is a fake: no network.
"""

from __future__ import annotations

import json
import smtplib

import pytest

from app.core.config import settings
from app.services import chat as chat_service
from app.services import connections, http_client, llm
from tests.conftest import register

GEMINI_KEY = "AIza-test-key-not-real"
LISTED = [
    "gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview", "gemini-2.5-flash-preview-tts", "gemini-2.5-flash-image", "gemini-3.1-flash-lite-image",
    "gemini-embedding-001",
]


def _json(status: int, body) -> http_client.HttpResponse:
    return http_client.HttpResponse(status, json.dumps(body).encode())


def _answer(text: str, finish: str = "STOP", thought: str | None = None) -> dict:
    parts = ([{"text": thought, "thought": True}] if thought else []) + [{"text": text}]
    return {"candidates": [{"content": {"parts": parts}, "finishReason": finish}]}


class FakeGemini:
    """generativelanguage.googleapis.com: `models` maps a model to its answer or to (status, message)."""

    def __init__(self, models: dict, listed: list[str] | None = None):
        self.models = models
        self.listed = LISTED if listed is None else listed
        self.calls: list[str] = []
        self.bodies: list[dict] = []

    def send(self, method, url, *, headers=None, json_body=None, form=None, data=None, timeout=15.0):
        assert headers == {"x-goog-api-key": GEMINI_KEY}
        if method == "GET" and url.startswith(f"{llm.GEMINI_MODELS_URL}?"):
            self.calls.append("list")
            return _json(200, {"models": [
                {"name": f"models/{name}",
                 "supportedGenerationMethods": ["embedContent"] if "embedding" in name else ["generateContent"]}
                for name in self.listed
            ]})

        assert method == "POST" and url.endswith(":generateContent")
        model = url[len(llm.GEMINI_MODELS_URL) + 1:].split(":")[0]
        self.calls.append(model)
        self.bodies.append(json_body)
        outcome = self.models.get(model, (404, f"models/{model} is not found for API version v1beta."))
        if isinstance(outcome, tuple):
            return _json(outcome[0], {"error": {"code": outcome[0], "message": outcome[1]}})
        return _json(200, outcome if isinstance(outcome, dict) else _answer(outcome))


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", GEMINI_KEY)
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "gemini_image_model", "gemini-2.5-flash-image")

    def install(models: dict, listed: list[str] | None = None) -> FakeGemini:
        fake = FakeGemini(models, listed)
        monkeypatch.setattr(http_client, "send", fake.send)
        return fake

    return install


# ============================================================
# Language-model client
# ============================================================

def test_retired_text_model_is_replaced_and_remembered(gemini):
    # gemini-2.5-flash is still listed, but answers 404 (seen in practice).
    fake = gemini({"gemini-3.8-flash": "A tip.", "gemini-3.6-flash": "Older."})

    assert llm.generate_text("system", "prompt", max_tokens=500) == "A tip."
    assert fake.calls == ["gemini-2.5-flash", "list", "gemini-3.8-flash"]
    assert fake.bodies[-1]["generationConfig"]["maxOutputTokens"] == 500 + llm.THINKING_ALLOWANCE_TOKENS

    # The choice is remembered: no second 404, no second list.
    assert llm.generate_text("system", "prompt") == "A tip."
    assert fake.calls[3:] == ["gemini-3.8-flash"]

    # When the replacement is retired too, the next one is found.
    del fake.models["gemini-3.8-flash"]
    assert llm.generate_text("system", "prompt") == "Older."
    assert fake.calls[4:] == ["gemini-3.8-flash", "list", "gemini-flash-latest", "gemini-3.1-flash-lite",
                              "gemini-3.6-flash"]


def test_replacement_moves_on_when_a_model_has_no_quota(gemini):
    fake = gemini({"gemini-3.8-flash": (429, "Quota exceeded, limit: 0"), "gemini-flash-latest": "From the alias."})
    reply = llm.ask_gemini({"contents": []})
    assert reply.ok and reply.model == "gemini-flash-latest" and reply.replaced
    assert fake.calls == ["gemini-2.5-flash", "list", "gemini-3.8-flash", "gemini-flash-latest"]


def test_replacement_gives_up_after_a_few_tries_and_never_picks_pro_or_speech_models(gemini):
    fake = gemini({})
    reply = llm.ask_gemini({"contents": []})
    assert not reply.ok and reply.status == 404
    assert fake.calls == ["gemini-2.5-flash", "list", "gemini-3.8-flash", "gemini-flash-latest",
                          "gemini-3.1-flash-lite"]
    assert llm.text_candidates([{"name": f"models/{n}", "supportedGenerationMethods": ["generateContent"]}
                                for n in LISTED + ["gemini-3-flash", "gemini-3-flash-preview"]]) == [
        "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview",
        "gemini-3.6-flash", "gemini-3-flash", "gemini-2.5-flash"]


def test_a_working_model_and_other_errors_do_not_trigger_a_search(gemini):
    fake = gemini({"gemini-2.5-flash": "Fine."})
    assert llm.generate_text("s", "p") == "Fine." and fake.calls == ["gemini-2.5-flash"]

    fake = gemini({"gemini-2.5-flash": (429, "Quota exceeded")})
    assert llm.generate_text("s", "p") is None and fake.calls == ["gemini-2.5-flash"]


def test_image_model_is_never_replaced(gemini, monkeypatch):
    monkeypatch.setattr(settings, "llm_image_enabled", True)
    fake = gemini({})
    assert llm.generate_image("a jar of cream") is None
    assert fake.calls == ["gemini-2.5-flash-image"]

    fake = gemini({"gemini-2.5-flash-image": {"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": "aGVsbG8="}}]}}]}})
    assert llm.generate_image("a jar of cream") == b"hello"
    assert fake.bodies[-1]["generationConfig"] == {"responseModalities": ["IMAGE"]}


def test_cut_off_and_thinking_parts(gemini):
    gemini({"gemini-2.5-flash": _answer("Half a senten", finish="MAX_TOKENS")})
    assert llm.generate_text("s", "p") is None  # an agent must not publish half a text

    assert llm.extract_text(_answer("Answer.", thought="Let me think")) == ("Answer.", False)
    assert llm.extract_text({"candidates": [{"finishReason": "MAX_TOKENS"}]}) == ("", True)
    assert llm.extract_text({"promptFeedback": {"blockReason": "SAFETY"}}) == ("", False)
    assert llm.extract_text(None) == ("", False)

    assert chat_service._close_cut_off_reply("First point.\nSecond point is unfin") == "First point.\n\n…"
    assert chat_service._close_cut_off_reply("One long paragraph that stops") == "One long paragraph that stops\n\n…"


def test_provider_messages_are_scrubbed(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", GEMINI_KEY)
    text = llm.clean_error(f"API key {GEMINI_KEY} is bad; also sk-proj-****abcd and   rk_live_51Hx. Use skincare.")
    assert text == "API key [key] is bad; also [key] and [key] Use skincare."


# ============================================================
# Connection tests (Admin -> Settings)
# ============================================================

@pytest.fixture
def admin_api(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    for name in ("llm_enabled", "llm_image_enabled"):
        monkeypatch.setattr(settings, name, False)
    for name in ("gemini_api_key", "openai_api_key", "google_client_id", "stripe_secret_key",
                 "stripe_webhook_secret", "paypal_client_id", "paypal_client_secret", "smtp_host", "smtp_from",
                 "safepay_api_key", "safepay_secret_key", "safepay_webhook_secret"):
        monkeypatch.setattr(settings, name, "")
    return client, register(client, "boss@test.com")


def _test(client, admin, name: str) -> dict:
    response = client.post(f"/admin/connections/{name}/test", headers=admin)
    assert response.status_code == 200, response.text
    return response.json()


def test_only_admins_can_test_and_nothing_is_called_when_nothing_is_set_up(admin_api, monkeypatch):
    client, admin = admin_api
    user = register(client, "user@test.com")
    assert client.post("/admin/connections/email/test", headers=user).status_code == 403
    assert client.post("/admin/connections/email/test").status_code == 401
    assert client.post("/admin/connections/nope/test", headers=admin).status_code == 404

    def no_network(*args, **kwargs):
        raise AssertionError("nothing may be sent while a service is not set up")

    monkeypatch.setattr(http_client, "send", no_network)
    monkeypatch.setattr(smtplib, "SMTP", no_network)

    payload = client.get("/admin/settings", headers=admin).json()
    assert payload["testable"] == sorted(connections.TESTS)
    for name in payload["testable"]:
        assert payload["integrations"][name] is False
        result = _test(client, admin, name)
        assert result["state"] == "not_set_up" and result["summary"].startswith("Set ")

    # An OpenAI key alone does not make the assistant's answers work.
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-proj-test-key")
    assert client.get("/admin/settings", headers=admin).json()["integrations"]["assistant_llm"] is False


def test_assistant_connection(admin_api, gemini):
    client, admin = admin_api

    gemini({"gemini-2.5-flash": "OK"})
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "working" and "gemini-2.5-flash answered" in result["summary"] and result["details"] == []

    gemini({"gemini-3.8-flash": "OK"})
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "working" and "gemini-3.8-flash answered" in result["summary"]
    assert "Set GEMINI_MODEL=gemini-3.8-flash" in result["details"][0]

    llm.reset()
    gemini({}, listed=["gemini-3.1-pro-preview"])
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "problem" and "not available to this key" in result["summary"]
    assert "No usable model" in result["details"][0]

    gemini({"gemini-2.5-flash": (429, "Quota exceeded for metric free_tier_requests, limit: 0")})
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "problem" and "quota" in result["summary"] and "limit: 0" in result["details"][1]

    gemini({"gemini-2.5-flash": (400, f"API key not valid: {GEMINI_KEY}")})
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "problem" and "did not accept GEMINI_API_KEY" in result["summary"]
    assert GEMINI_KEY not in json.dumps(result) and "[key]" in result["details"][1]


def test_assistant_connection_when_google_is_unreachable(admin_api, gemini, monkeypatch):
    client, admin = admin_api
    gemini({})

    def offline(*args, **kwargs):
        raise http_client.HttpError("Request failed: URLError")

    monkeypatch.setattr(http_client, "send", offline)
    result = _test(client, admin, "assistant_llm")
    assert result["state"] == "problem" and "could not be reached" in result["summary"]


def test_image_connection(admin_api, gemini, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "llm_image_enabled", True)

    fake = gemini({})
    result = _test(client, admin, "assistant_images")
    assert result["state"] == "working" and "gemini-2.5-flash-image is available" in result["summary"]
    assert "No image was made" in result["details"][0]
    assert fake.calls == ["list"]  # nothing was generated, so nothing was billed

    monkeypatch.setattr(settings, "gemini_image_model", "gemini-2.0-flash-preview-image-generation")
    result = _test(client, admin, "assistant_images")
    assert result["state"] == "problem"
    assert result["details"] == ["Set GEMINI_IMAGE_MODEL to one of: gemini-2.5-flash-image, gemini-3.1-flash-lite-image."]

    # OpenAI as the image provider
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "sk-proj-test-key")
    monkeypatch.setattr(settings, "openai_image_model", "gpt-image-1")
    answers = {"model": 404}

    def openai(method, url, *, headers=None, **kwargs):
        assert method == "GET" and headers == {"Authorization": "Bearer sk-proj-test-key"}
        if url == "https://api.openai.com/v1/models":
            return _json(200, {"data": [{"id": "gpt-image-2"}, {"id": "gpt-5.5"}, {"id": "gpt-image-2-mini"}]})
        assert url == "https://api.openai.com/v1/models/gpt-image-1"
        return _json(answers["model"], {"error": {"message": "The model does not exist"}} if answers["model"] != 200
                     else {"id": "gpt-image-1"})

    monkeypatch.setattr(http_client, "send", openai)
    result = _test(client, admin, "assistant_images")
    assert result["state"] == "problem"
    assert result["details"] == ["Set OPENAI_IMAGE_MODEL to one of: gpt-image-2, gpt-image-2-mini."]

    answers["model"] = 401
    assert "did not accept OPENAI_API_KEY" in _test(client, admin, "assistant_images")["summary"]
    answers["model"] = 200
    assert _test(client, admin, "assistant_images")["state"] == "working"


def test_google_connection(admin_api, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "google_client_id", "not-a-client-id")
    result = _test(client, admin, "google_sign_in")
    assert result["state"] == "problem" and "does not look like" in result["summary"]

    monkeypatch.setattr(settings, "google_client_id", "1234-abc.apps.googleusercontent.com")
    monkeypatch.setattr(http_client, "send", lambda *a, **k: _json(200, {"keys": [{"kid": "k1", "kty": "RSA"}]}))
    result = _test(client, admin, "google_sign_in")
    assert result["state"] == "working" and "Authorised JavaScript origins" in result["details"][0]

    monkeypatch.setattr(http_client, "send", lambda *a, **k: _json(503, {}))
    assert _test(client, admin, "google_sign_in")["state"] == "problem"


def test_stripe_connection(admin_api, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_abc12")
    status = {"code": 200}

    def stripe(method, url, *, headers=None, **kwargs):
        assert (method, url) == ("GET", "https://api.stripe.com/v1/checkout/sessions?limit=1")
        assert headers == {"Authorization": "Bearer sk_test_abc12"}
        if status["code"] == 200:
            return _json(200, {"object": "list", "data": [], "has_more": False})
        return _json(status["code"], {"error": {"message": "Invalid API Key provided: sk_test_****c123"}})

    monkeypatch.setattr(http_client, "send", stripe)
    result = _test(client, admin, "card_payments")
    assert result["state"] == "working" and "test mode" in result["summary"]
    assert "STRIPE_WEBHOOK_SECRET is not set" in result["details"][0]

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    assert _test(client, admin, "card_payments")["details"] == []

    status["code"] = 401
    result = _test(client, admin, "card_payments")
    assert result["state"] == "problem" and "did not accept STRIPE_SECRET_KEY" in result["summary"]
    status["code"] = 403
    assert "restricted key" in _test(client, admin, "card_payments")["details"][0]
    status["code"] = 500
    result = _test(client, admin, "card_payments")
    assert "HTTP 500" in result["summary"] and "sk_test" not in json.dumps(result)


def test_paypal_connection(admin_api, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "paypal_client_id", "client")
    monkeypatch.setattr(settings, "paypal_client_secret", "pp-secret")
    monkeypatch.setattr(settings, "paypal_mode", "sandbox")
    monkeypatch.setattr(settings, "shop_currency", "PKR")
    monkeypatch.setattr(settings, "paypal_currency", "USD")
    monkeypatch.setattr(settings, "paypal_exchange_rate", 0.0)
    accepted = {"yes": True}

    def paypal(method, url, *, headers=None, form=None, **kwargs):
        assert (method, url) == ("POST", "https://api-m.sandbox.paypal.com/v1/oauth2/token")
        assert form == {"grant_type": "client_credentials"} and headers["Authorization"].startswith("Basic ")
        if accepted["yes"]:
            return _json(200, {"access_token": "token"})
        return _json(401, {"error": "invalid_client", "error_description": "Client Authentication failed"})

    monkeypatch.setattr(http_client, "send", paypal)
    result = _test(client, admin, "paypal")
    assert result["state"] == "problem" and "cannot charge PKR" in result["summary"]
    assert "PAYPAL_EXCHANGE_RATE" in result["details"][0]

    monkeypatch.setattr(settings, "paypal_exchange_rate", 280.0)
    result = _test(client, admin, "paypal")
    assert result["state"] == "working" and "sandbox" in result["summary"]

    accepted["yes"] = False
    result = _test(client, admin, "paypal")
    assert result["state"] == "problem" and "for the sandbox environment" in result["summary"]
    assert "pp-secret" not in json.dumps(result)


def test_safepay_connection(admin_api, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "safepay_api_key", "sec_public")
    monkeypatch.setattr(settings, "safepay_secret_key", "sfpy-secret")
    monkeypatch.setattr(settings, "safepay_environment", "sandbox")
    monkeypatch.setattr(settings, "shop_currency", "PKR")
    monkeypatch.setattr(settings, "card_provider", "auto")
    status = {"code": 200}

    def safepay(method, url, *, headers=None, json_body=None, **kwargs):
        assert (method, url) == ("POST", "https://sandbox.api.getsafepay.com/client/passport/v1/token")
        assert headers == {"X-SFPY-MERCHANT-SECRET": "sfpy-secret"}
        return _json(status["code"], {"data": "tbt-token"} if status["code"] == 200 else {"error": "unauthorized"})

    monkeypatch.setattr(http_client, "send", safepay)
    result = _test(client, admin, "safepay")
    assert result["state"] == "working" and "sandbox" in result["summary"]
    assert any("SAFEPAY_WEBHOOK_SECRET is not set" in line for line in result["details"])

    status["code"] = 401
    result = _test(client, admin, "safepay")
    assert result["state"] == "problem" and "did not accept SAFEPAY_SECRET_KEY" in result["summary"]
    assert "sfpy-secret" not in json.dumps(result)

    status["code"] = 200
    monkeypatch.setattr(settings, "shop_currency", "INR")
    assert "cannot charge INR" in _test(client, admin, "safepay")["summary"]


class FakeMailServer:
    log: list[str] = []
    fail: str | None = None

    def __init__(self, host, port, timeout=None, **kwargs):
        if FakeMailServer.fail == "connect":
            raise ConnectionRefusedError("refused")
        FakeMailServer.log.append(f"connect {host}:{port}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        FakeMailServer.log.append("quit")
        return False

    def starttls(self, context=None):
        FakeMailServer.log.append("starttls")

    def login(self, username, password):
        if FakeMailServer.fail == "login":
            raise smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        FakeMailServer.log.append(f"login {username}")

    def noop(self):
        FakeMailServer.log.append("noop")

    def send_message(self, message):
        FakeMailServer.log.append("send")


def test_email_connection_logs_in_without_sending(admin_api, monkeypatch):
    client, admin = admin_api
    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_from", "clinic@example.com")
    monkeypatch.setattr(settings, "smtp_username", "clinic@example.com")
    monkeypatch.setattr(settings, "smtp_password", "app-pass")
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    monkeypatch.setattr(smtplib, "SMTP", FakeMailServer)
    monkeypatch.setattr(FakeMailServer, "log", [])
    monkeypatch.setattr(FakeMailServer, "fail", None)

    result = _test(client, admin, "email")
    assert result["state"] == "working" and "smtp.gmail.com:587 accepted the login" in result["summary"]
    assert FakeMailServer.log == ["connect smtp.gmail.com:587", "starttls", "login clinic@example.com", "noop", "quit"]

    monkeypatch.setattr(FakeMailServer, "fail", "login")
    result = _test(client, admin, "email")
    assert result["state"] == "problem" and "app password" in result["details"][0]
    assert "app-pass" not in json.dumps(result)

    monkeypatch.setattr(FakeMailServer, "fail", "connect")
    result = _test(client, admin, "email")
    assert result["state"] == "problem" and "ConnectionRefusedError" in result["summary"]


def test_a_crashing_test_is_reported_not_raised(admin_api, monkeypatch):
    client, admin = admin_api

    def boom():
        raise RuntimeError("unexpected")

    monkeypatch.setitem(connections.TESTS, "email", boom)
    result = _test(client, admin, "email")
    assert result["state"] == "problem" and "test itself failed" in result["summary"]
