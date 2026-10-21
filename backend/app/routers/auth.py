import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import PasswordResetToken, User
from app.dependencies import get_current_user
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# REQ-6.10 / Security: basic brute-force protection via in-memory lockout.
# For production, back this with Redis or a DB table instead of a dict.
_failed_attempts: dict[str, list[datetime]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def _is_locked_out(email: str) -> bool:
    attempts = _failed_attempts.get(email, [])
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    recent = [a for a in attempts if a > cutoff]
    _failed_attempts[email] = recent
    return len(recent) >= MAX_FAILED_ATTEMPTS


def _record_failed_attempt(email: str) -> None:
    _failed_attempts.setdefault(email, []).append(datetime.now(timezone.utc))


def _clear_failed_attempts(email: str) -> None:
    _failed_attempts.pop(email, None)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An account with this email already exists.")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if _is_locked_out(payload.email):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed login attempts. Please try again in a few minutes.",
        )

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _record_failed_attempt(payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    _clear_failed_attempts(payload.email)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    REQ-6.8: password reset via email.

    No email provider is wired up yet, so this generates a reset token and
    returns it directly in the response for local development/testing. Swap
    the final line for an actual email send (e.g. via an SMTP or transactional
    email service) before going to production, and stop returning the token.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    # Always respond the same way whether or not the account exists, to avoid
    # leaking which emails are registered.
    generic_response = {"message": "If an account exists for this email, a reset link has been sent."}
    if not user:
        return generic_response

    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(reset)
    db.commit()

    generic_response["dev_reset_token"] = token  # TODO: remove once email sending is wired up
    return generic_response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    if not reset or reset.used or reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user.password_hash = hash_password(payload.new_password)
    reset.used = True
    db.commit()
    return {"message": "Password has been reset. You can now log in with your new password."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """REQ-6.9: allow users to delete their account and associated data."""
    db.delete(current_user)
    db.commit()
