from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas import NotificationSettingsRequest, ProfileUpdateRequest, UserOut
from app.services import rate_limit
from app.services.uploads import delete_upload, save_upload

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=UserOut)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """REQ-6.4 / REQ-6.7: allow updating profile info incl. skin type."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.skin_type is not None:
        current_user.skin_type = payload.skin_type

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/notifications", response_model=UserOut)
def update_notifications(
    payload: NotificationSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """REQ-6.5: store notification preferences."""
    current_user.notify_analysis = payload.notify_analysis
    current_user.notify_reports = payload.notify_reports
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/avatar", response_model=UserOut)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Avatar upload uses the same validated, private storage as analyses."""
    rate_limit.enforce(db, "avatar", current_user.id, 20)

    new_url = save_upload(file, "avatars")
    old_url = current_user.avatar_url

    current_user.avatar_url = new_url
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_upload(new_url)
        raise

    db.refresh(current_user)

    if old_url and old_url != new_url:
        delete_upload(old_url)

    return current_user
