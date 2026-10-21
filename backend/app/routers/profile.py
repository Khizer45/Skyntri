import shutil
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas import NotificationSettingsRequest, ProfileUpdateRequest, UserOut

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
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please upload a JPEG, PNG, or WebP image.")

    avatars_dir = settings.upload_path / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = avatars_dir / filename

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return current_user
