from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import ContactMessage, User
from app.dependencies import require_admin
from app.schemas import ContactMessageOut, ContactMessageRequest, ContactSubmitOut
from app.services import rate_limit

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactSubmitOut, status_code=status.HTTP_201_CREATED)
def submit_contact_message(
    payload: ContactMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public contact/help form (SK-13). Rate limited per client IP.

    The response only confirms receipt; it never echoes stored messages
    (SEC-ACL-005).
    """
    rate_limit.enforce(
        db,
        "contact_ip",
        rate_limit.client_ip(request),
        settings.contact_per_hour,
        message="Too many messages. Please try again later.",
    )

    message = ContactMessage(
        name=payload.name.strip(),
        email=str(payload.email).strip().lower(),
        subject=payload.subject.strip(),
        message=payload.message.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return ContactSubmitOut(
        id=message.id,
        created_at=message.created_at,
        message="Thank you. Your message has been received.",
    )


# ============================================================
# Administrator-only management (SK-01 / SEC-AUTH-004)
# ============================================================

@router.get("", response_model=list[ContactMessageOut])
def list_contact_messages(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(ContactMessage)
        .order_by(desc(ContactMessage.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{message_id}", response_model=ContactMessageOut)
def get_contact_message(
    message_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    return message


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_message(
    message_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    db.delete(message)
    db.commit()
