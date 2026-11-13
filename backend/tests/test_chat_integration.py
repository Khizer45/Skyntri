from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


def test_chat_integration(tmp_path, monkeypatch):
    # ---------------------------------------------------------
    # Create isolated temporary SQLite database
    # ---------------------------------------------------------
    test_db_path = tmp_path / "test_chat.db"

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

    # Prevent application startup from touching the real database
    monkeypatch.setattr(
        "app.main.initialize_database",
        lambda: None,
    )


    # ---------------------------------------------------------
    # Disable external Gemini call.
    #
    # Returning None makes the actual chat service use its
    # local rule-based fallback.
    # ---------------------------------------------------------
    monkeypatch.setattr(
        "app.services.chat._generate_gemini_reply",
        lambda message, history, user_context, language=None: None,
    )

    try:
        with TestClient(app) as client:

            # -------------------------------------------------
            # 1. Register test user
            # -------------------------------------------------
            register_response = client.post(
                "/auth/register",
                json={
                    "full_name": "Chat Integration User",
                    "email": "chat-integration@test.com",
                    "password": "TestPassword123!",
                },
            )

            assert register_response.status_code == 201

            access_token = (
                register_response.json()["access_token"]
            )

            auth_headers = {
                "Authorization": f"Bearer {access_token}"
            }

            # -------------------------------------------------
            # 2. Send skincare question
            # -------------------------------------------------
            chat_response = client.post(
                "/chat",
                headers=auth_headers,
                json={
                    "message": "I have acne. What skincare routine should I use?"
                },
            )

            # -------------------------------------------------
            # 3. Verify successful response
            # -------------------------------------------------
            assert chat_response.status_code == 201

            chat_data = chat_response.json()

            assert "id" in chat_data
            assert chat_data["role"] == "assistant"
            assert chat_data["content"]

            # The local acne response should mention acne-related care
            assert (
                "acne" in chat_data["content"].casefold()
            )

            # Health-related responses should contain disclaimer
            assert (
                "not a medical diagnosis"
                in chat_data["content"]
            )

            # -------------------------------------------------
            # 4. Verify chat history
            # -------------------------------------------------
            history_response = client.get(
                "/chat/history",
                headers=auth_headers,
            )

            assert history_response.status_code == 200

            history = history_response.json()

            assert len(history) == 2

            assert history[0]["role"] == "user"
            assert (
                history[0]["content"]
                == "I have acne. What skincare routine should I use?"
            )

            assert history[1]["role"] == "assistant"
            assert history[1]["content"]

            # -------------------------------------------------
            # 5. Verify both messages are stored in database
            # -------------------------------------------------
            from app.db.models import ChatMessage

            db = TestSessionLocal()

            try:
                saved_messages = (
                    db.query(ChatMessage)
                    .order_by(ChatMessage.created_at.asc())
                    .all()
                )

                assert len(saved_messages) == 2

                assert (
                    saved_messages[0].role
                    == "user"
                )

                assert (
                    saved_messages[1].role
                    == "assistant"
                )

                assert (
                    saved_messages[0].content
                    == "I have acne. What skincare routine should I use?"
                )

            finally:
                db.close()

            # -------------------------------------------------
            # 6. Verify protected endpoint rejects no-token access
            # -------------------------------------------------
            unauthorized_response = client.get(
                "/chat/history",
            )

            assert unauthorized_response.status_code == 401

    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()

# ---------------------------------------------------------------------------
# Tables, reply language and illustrations
# ---------------------------------------------------------------------------

def _png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (96, 96), (200, 220, 210)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_routine_answer_is_a_markdown_table(api):
    from tests.conftest import register

    client, _ = api
    headers = register(client, "table@test.com")
    reply = client.post("/chat", json={"message": "What skincare routine should I follow?"}, headers=headers)
    assert reply.status_code == 201
    assert "| Step | Morning | Evening |" in reply.json()["content"]


def test_reply_language_reaches_the_model(api, monkeypatch):
    from app.core.config import settings
    from app.services import http_client, llm
    from tests.conftest import register

    client, _ = api
    headers = register(client, "lang@test.com")
    assert client.post("/chat", json={"message": "hello", "language": "klingon"}, headers=headers).status_code == 422

    seen = {}
    answer = {"text": "Jawab", "finish": "STOP"}

    def fake_send(method, url, *, headers=None, json_body=None, form=None, data=None, timeout=15.0):
        import json as _json
        assert url == f"{llm.GEMINI_MODELS_URL}/gemini-2.5-flash:generateContent"
        assert headers == {"x-goog-api-key": "test-key"}
        seen["system"] = json_body["systemInstruction"]["parts"][0]["text"]
        seen["limit"] = json_body["generationConfig"]["maxOutputTokens"]
        body = {"candidates": [{"content": {"parts": [{"text": answer["text"]}]}, "finishReason": answer["finish"]}]}
        return http_client.HttpResponse(200, _json.dumps(body).encode())

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "llm_max_output_tokens", 1500)
    monkeypatch.setattr(http_client, "send", fake_send)

    reply = client.post("/chat", json={"message": "Meri skin oily hai", "language": "roman_ur"}, headers=headers)
    assert reply.json()["content"].startswith("Jawab")
    assert seen["system"].endswith("Reply language: Roman Urdu (Urdu written with Latin letters).")
    assert "FYP" not in seen["system"] and "student" not in seen["system"]
    # Room for the model's thinking is added to the wanted answer size.
    assert seen["limit"] == 1500 + llm.THINKING_ALLOWANCE_TOKENS
    client.post("/chat", json={"message": "My skin is oily"}, headers=headers)
    assert "Reply language" not in seen["system"]

    # A long answer (a routine with a table) is kept whole.
    answer["text"] = "Line about skin care.\n" * 300
    long_reply = client.post("/chat", json={"message": "Give me a full routine"}, headers=headers).json()["content"]
    assert len(long_reply) > 6000

    # An answer the model could not finish loses its half-written last row and is marked.
    answer.update(text="| Step | Morning |\n| --- | --- |\n| Cleanse | Gentle cleanser |\n| Moisturise | Light cr",
                  finish="MAX_TOKENS")
    cut = client.post("/chat", json={"message": "Routine as a table"}, headers=headers).json()["content"]
    assert "| Cleanse | Gentle cleanser |" in cut and "Light cr" not in cut and "\n\n…" in cut


def test_image_request_without_provider_explains(api):
    from tests.conftest import register

    client, _ = api
    headers = register(client, "noimg@test.com")
    assert client.get("/chat/capabilities", headers=headers).json()["images"] is False
    reply = client.post("/chat", json={"message": "make a imge of skin care"}, headers=headers).json()
    assert reply["image_url"] is None and "can't create images" in reply["content"]


def test_image_request_generates_private_image_with_daily_limit(api, monkeypatch):
    from app.core.config import settings
    from app.services import llm
    from tests.conftest import register

    client, _ = api
    headers = register(client, "img@test.com")
    prompts = []

    def fake_image(prompt):
        prompts.append(prompt)
        return _png_bytes()

    monkeypatch.setattr(settings, "llm_image_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "chat_images_per_day", 1)
    monkeypatch.setattr(llm, "generate_image", fake_image)
    assert client.get("/chat/capabilities", headers=headers).json()["images"] is True

    reply = client.post("/chat", json={"message": "Draw a picture of a morning routine"}, headers=headers).json()
    assert reply["image_url"].startswith("/files/") and "sig=" in reply["image_url"]
    assert client.get(reply["image_url"]).status_code == 200
    # The user's words are wrapped in fixed safety rules.
    assert "Do not show real or recognisable people" in prompts[0] and "morning routine" in prompts[0]

    second = client.post("/chat", json={"message": "Create an image of sunscreen"}, headers=headers).json()
    assert second["image_url"] is None and "limit" in second["content"]

    # Clearing the conversation also removes the stored image.
    stored = list((settings.upload_path / "chat_images").iterdir())
    assert len(stored) == 1
    assert client.delete("/chat/history", headers=headers).status_code == 204
    assert list((settings.upload_path / "chat_images").iterdir()) == []

    # A normal question is not treated as an image request.
    plain = client.post("/chat", json={"message": "How do I reduce acne?"}, headers=headers).json()
    assert plain["image_url"] is None and len(prompts) == 1
