from fastapi import APIRouter, Depends, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ContactMessage
from app.schemas import ContactMessageOut, ContactMessageRequest

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactMessageOut, status_code=status.HTTP_201_CREATED)
def submit_contact_message(payload: ContactMessageRequest, db: Session = Depends(get_db)):
    """
    Stores a message submitted via the Contact/Help form.

    NOTE: This only persists the message to the database. To actually notify
    the team, add an email-send call here (e.g. via SMTP or a transactional
    email API) once you have a provider set up.
    """
    message = ContactMessage(**payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[ContactMessageOut])
def list_contact_messages(db: Session = Depends(get_db)):
    """
    Simple listing endpoint, useful for an admin view later.
    NOTE: not access-controlled yet — restrict to an admin role before
    exposing this publicly, per the SRS's admin-only requirement.
    """
    return db.query(ContactMessage).order_by(desc(ContactMessage.created_at)).all()
