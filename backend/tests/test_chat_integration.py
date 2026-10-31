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
        lambda message, history, user_context: None,
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