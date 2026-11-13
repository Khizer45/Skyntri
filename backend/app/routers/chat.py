from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import ChatMessage, IngredientScan, SkinAnalysis, User
from app.dependencies import get_current_user
from app.schemas import ChatMessageOut, ChatRequest
from app.services import llm, rate_limit
from app.services.chat import (
    MAX_HISTORY_MESSAGES,
    MAX_USER_MESSAGE_LENGTH,
    REPLY_LANGUAGES,
    build_image_prompt,
    get_assistant_reply,
    is_image_request,
)
from app.services.uploads import delete_upload, save_image_bytes


router = APIRouter(
    prefix="/chat",
    tags=["ai-assistant"],
)


# ============================================================================
# Send Message
# ============================================================================

@router.post(
    "",
    response_model=ChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message to the Skyntri AI assistant.

    Flow:

        Frontend
            ↓
        User message
            ↓
        Save user message
            ↓
        Load recent conversation
            ↓
        Load latest Skyntri context
            ↓
        Safety checks
            ↓
        Gemini
            ↓
        If Gemini fails → local fallback
            ↓
        Save assistant response
            ↓
        Return assistant message

    The external Gemini API is optional. The local fallback keeps the
    assistant functional when the API is unavailable.
    """

    rate_limit.enforce(
        db,
        "chat",
        current_user.id,
        settings.chat_per_hour,
        message="Message limit reached. Please wait a while before sending more messages.",
    )

    message = (payload.message or "").strip()

    # ------------------------------------------------------------------------
    # Validate message
    # ------------------------------------------------------------------------

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    if len(message) > MAX_USER_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Message is too long. "
                f"Please keep it under {MAX_USER_MESSAGE_LENGTH} characters."
            ),
        )

    # ------------------------------------------------------------------------
    # Save user message
    # ------------------------------------------------------------------------

    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=message,
    )

    try:
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save your message.",
        ) from exc

    # ------------------------------------------------------------------------
    # Load recent conversation
    # ------------------------------------------------------------------------

    history_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
        )
        .order_by(
            asc(ChatMessage.created_at),
        )
        .all()
    )

    recent_messages = history_messages[-MAX_HISTORY_MESSAGES:]

    history_payload = [
        {
            "role": message_item.role,
            "content": message_item.content,
        }
        for message_item in recent_messages
        if message_item.role in {"user", "assistant"}
        and message_item.content
    ]

    # ------------------------------------------------------------------------
    # Load latest Skyntri context
    # ------------------------------------------------------------------------

    try:
        latest_analysis = (
            db.query(SkinAnalysis)
            .filter(
                SkinAnalysis.user_id == current_user.id,
            )
            .order_by(
                SkinAnalysis.created_at.desc(),
            )
            .first()
        )

        latest_scan = (
            db.query(IngredientScan)
            .filter(
                IngredientScan.user_id == current_user.id,
            )
            .order_by(
                IngredientScan.created_at.desc(),
            )
            .first()
        )

        # --------------------------------------------------------------------
        # Parse latest ingredient scan details safely
        # --------------------------------------------------------------------

        scan_details = {}

        if latest_scan and latest_scan.details_json:
            try:
                parsed_details = json.loads(
                    latest_scan.details_json
                )

                if isinstance(parsed_details, dict):
                    scan_details = parsed_details

            except (TypeError, ValueError, json.JSONDecodeError):
                scan_details = {}

        # --------------------------------------------------------------------
        # Build context for the AI assistant
        # --------------------------------------------------------------------

        user_context = {
            "latest_analysis": {
                "condition": (
                    latest_analysis.predicted_condition
                    if latest_analysis
                    else ""
                ),
                "severity": (
                    latest_analysis.severity_level
                    if latest_analysis
                    else ""
                ),
            },
            "latest_scan": {
                "matched_ingredients": scan_details.get(
                    "matched_ingredients",
                    [],
                ),
                "safety_label": scan_details.get(
                    "safety_label",
                    "",
                ),
            },
        }

    except Exception:
        # Context is helpful but must never prevent the assistant from
        # responding. Use empty context if database/context loading fails.
        user_context = {}

    # ------------------------------------------------------------------------
    # Generate assistant response
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    # Illustration requests ("make an image of a morning routine")
    # ------------------------------------------------------------------------

    image_ref = None
    image_note = None

    if is_image_request(message):
        if llm.image_provider() is None:
            image_note = (
                "I can't create images here yet: image generation has not been switched on "
                "for this clinic. I can still explain it in words or as a table."
            )
        elif rate_limit.is_limited(
            db, "chat_image", current_user.id, settings.chat_images_per_day, timedelta(days=1)
        ):
            image_note = "You have reached today's limit for images. Please try again tomorrow."
        else:
            rate_limit.record_event(db, "chat_image", current_user.id)
            image_bytes = llm.generate_image(build_image_prompt(message))
            if image_bytes:
                try:
                    image_ref = save_image_bytes(image_bytes, "chat_images")
                except HTTPException:
                    image_ref = None
            if image_ref is None:
                image_note = "I could not create that image this time. Please try again in a moment."

    try:
        if image_ref is not None:
            reply_text = "Here is the illustration you asked for."
        elif image_note is not None:
            reply_text = image_note
        else:
            reply_text = get_assistant_reply(
                message=message,
                history=history_payload,
                user_context=user_context,
                language=None if payload.language == "auto" else payload.language,
            )

    except Exception as exc:
        # The service is designed to use local fallback when Gemini fails.
        # This catch protects the API route from unexpected service errors.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI assistant could not generate a response.",
        ) from exc

    # ------------------------------------------------------------------------
    # Prevent accidental empty responses
    # ------------------------------------------------------------------------

    if not reply_text or not reply_text.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI assistant returned an empty response.",
        )

    reply_text = reply_text.strip()

    # ------------------------------------------------------------------------
    # Save assistant response
    # ------------------------------------------------------------------------

    assistant_msg = ChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=reply_text,
        image_url=image_ref,
    )

    try:
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the assistant response.",
        ) from exc

    return assistant_msg


# ============================================================================
# Capabilities
# ============================================================================

@router.get("/capabilities")
def chat_capabilities(_user: User = Depends(get_current_user)):
    """What the assistant can do with the current server configuration."""
    return {
        "llm": llm.text_available(),
        "images": llm.image_provider() is not None,
        "languages": [{"id": "auto", "label": "Auto"}]
        + [{"id": key, "label": label.split(",")[0].split(" (")[0]} for key, label in REPLY_LANGUAGES.items()],
    }


# ============================================================================
# Chat History
# ============================================================================

@router.get(
    "/history",
    response_model=list[ChatMessageOut],
)
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated user's complete chat history.

    Every query is filtered using the authenticated user's ID, so one user
    cannot access another user's chat messages.
    """

    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
        )
        .order_by(
            asc(ChatMessage.created_at),
        )
        .all()
    )


# ============================================================================
# Clear Chat History
# ============================================================================

@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete all chat messages belonging to the authenticated user.
    """

    try:
        image_refs = [
            row[0]
            for row in db.query(ChatMessage.image_url).filter(
                ChatMessage.user_id == current_user.id,
                ChatMessage.image_url.isnot(None),
            )
        ]

        db.query(ChatMessage).filter(
            ChatMessage.user_id == current_user.id,
        ).delete(
            synchronize_session=False,
        )

        db.commit()

        for ref in image_refs:
            delete_upload(ref)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not clear chat history.",
        ) from exc

    return None