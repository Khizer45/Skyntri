from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    dummy_verify_password,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import Appointment, DoctorProfile, PasswordResetToken, User
from app.dependencies import get_current_user
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import google_auth, rate_limit
from app.services.email import EmailDeliveryError, send_password_reset_email
from app.services.user_files import collect_user_file_refs, remove_files

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("skyntri.auth")

GENERIC_RESET_RESPONSE = {
    "message": "If an account exists for this email, a reset link has been sent."
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _apply_admin_bootstrap(user: User) -> bool:
    """Grant the admin role to e-mails listed in ADMIN_EMAILS (server-side)."""
    if user.email.lower() in settings.admin_email_list and user.role != "admin":
        user.role = "admin"
        return True
    return False


def _find_user(db: Session, email: str) -> User | None:
    normalized = _normalize_email(email)
    user = db.query(User).filter(User.email == normalized).first()
    if user is None and normalized != email:
        # Accounts created before e-mails were normalised.
        user = db.query(User).filter(User.email == email).first()
    return user


# ============================================================
# Register / login
# ============================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit.enforce(
        db,
        "register_ip",
        rate_limit.client_ip(request),
        20,
        message="Too many sign-up attempts. Please try again later.",
    )

    email = _normalize_email(payload.email)

    if _find_user(db, email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An account with this email already exists.")

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    _apply_admin_bootstrap(user)

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    SK-07: failed logins are counted in the shared database per e-mail
    (rolling window, no permanent lock-out) and all attempts per IP.
    """
    email = _normalize_email(payload.email)
    window = timedelta(minutes=settings.login_window_minutes)
    ip = rate_limit.client_ip(request)

    if rate_limit.is_limited(db, "login_fail", email, settings.login_max_failures, window):
        raise rate_limit.too_many_requests(
            "Too many failed login attempts. Please try again in a few minutes.",
            retry_after=int(window.total_seconds()),
        )

    rate_limit.enforce(
        db,
        "login_ip",
        ip,
        settings.login_ip_max_attempts,
        window,
        message="Too many login attempts from this network. Please try again later.",
    )

    user = _find_user(db, email)

    if user is None:
        dummy_verify_password(payload.password)
        rate_limit.record_event(db, "login_fail", email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    if not verify_password(payload.password, user.password_hash):
        rate_limit.record_event(db, "login_fail", email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    rate_limit.clear_events(db, "login_fail", email)

    if _apply_admin_bootstrap(user):
        db.commit()
        db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ============================================================
# Password reset (SK-02 / SEC-AUTH-007)
# ============================================================

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Send a single-use, short-lived reset link by e-mail.

    * The response is identical whether or not the account exists.
    * The token is never returned by the API; only its SHA-256 hash is stored.
    * In production, password reset is disabled (HTTP 503) until SMTP is
      configured, instead of exposing a development token.
    """
    if settings.is_production and not settings.smtp_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset is temporarily unavailable. Please contact support.",
        )

    email = _normalize_email(payload.email)

    rate_limit.enforce(
        db,
        "forgot_ip",
        rate_limit.client_ip(request),
        settings.forgot_password_per_hour,
        message="Too many reset requests. Please try again later.",
    )

    # Per-e-mail limit is applied silently so it cannot be used to discover
    # whether an account exists.
    if rate_limit.is_limited(db, "forgot_email", email, 3, timedelta(hours=1)):
        return dict(GENERIC_RESET_RESPONSE)
    rate_limit.record_event(db, "forgot_email", email)

    user = _find_user(db, email)
    if not user or not user.is_active:
        return dict(GENERIC_RESET_RESPONSE)

    now = datetime.now(timezone.utc)

    # Only the newest link is valid.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).update({PasswordResetToken.used: True}, synchronize_session=False)

    raw_token = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token=hash_opaque_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_token_minutes),
        )
    )
    db.commit()

    reset_link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw_token}"

    try:
        send_password_reset_email(user.email, user.full_name, reset_link)
    except EmailDeliveryError:
        logger.error("password_reset_email_failed", extra={"event": "password_reset_email_failed"})

    return dict(GENERIC_RESET_RESPONSE)


def _as_aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes even for timezone=True columns.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit.enforce(
        db,
        "reset_ip",
        rate_limit.client_ip(request),
        settings.reset_password_per_hour,
        message="Too many attempts. Please try again later.",
    )

    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    reset = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == hash_opaque_token(payload.token))
        .first()
    )

    if not reset or reset.used or _as_aware(reset.expires_at) < datetime.now(timezone.utc):
        raise invalid

    user = db.get(User, reset.user_id)
    if not user or not user.is_active:
        raise invalid

    user.password_hash = hash_password(payload.new_password)
    # The link was sent to the address, so the address is proven.
    user.password_set = True
    user.email_verified = True
    reset.used = True

    # Invalidate any other outstanding links for this account.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).update({PasswordResetToken.used: True}, synchronize_session=False)

    db.commit()
    rate_limit.clear_events(db, "login_fail", user.email)

    return {"message": "Password has been reset. You can now log in with your new password."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.password_set:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This account has no password yet. Choose one under Settings first.",
        )
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@router.post("/set-password")
def set_password(
    payload: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Choose a first password for an account that was created with Google."""
    if current_user.password_set:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This account already has a password. Use 'Change password'.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_set = True
    db.commit()
    return {"message": "Password saved. You can now also sign in with your e-mail and password."}


# ============================================================
# Sign in with Google
# ============================================================

def _unusable_password_hash() -> str:
    return hash_password(generate_opaque_token())


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Exchange a Google ID token for a Skyntri session.

    * The token is verified on the server (signature, audience, issuer,
      expiry, verified e-mail). Nothing else from the browser is trusted.
    * An existing account with the same verified address is linked. If that
      account never proved its address, its password is discarded, so
      someone who registered the address first cannot keep access.
    """
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Sign in with Google is not set up.")

    rate_limit.enforce(
        db,
        "google_login_ip",
        rate_limit.client_ip(request),
        settings.login_ip_max_attempts,
        timedelta(minutes=settings.login_window_minutes),
        message="Too many sign-in attempts from this network. Please try again later.",
    )

    try:
        identity = google_auth.verify_id_token(payload.credential)
    except google_auth.GoogleAuthUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Google sign-in is temporarily unavailable."
        ) from None
    except google_auth.GoogleAuthError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google sign-in failed. Please try again.") from None

    user = db.query(User).filter(User.google_sub == identity["sub"]).first()

    if user is None:
        user = _find_user(db, identity["email"])
        if user is not None:
            if user.google_sub and user.google_sub != identity["sub"]:
                raise HTTPException(status.HTTP_409_CONFLICT, "This e-mail is linked to another Google account.")
            if not user.email_verified:
                user.password_hash = _unusable_password_hash()
                user.password_set = False
            user.google_sub = identity["sub"]
            user.email_verified = True
        else:
            user = User(
                full_name=identity["name"] or identity["email"].split("@")[0],
                email=identity["email"],
                password_hash=_unusable_password_hash(),
                password_set=False,
                email_verified=True,
                google_sub=identity["sub"],
                is_active=True,
                role="user",
            )
            db.add(user)

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    _apply_admin_bootstrap(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(subject=user.id), user=UserOut.model_validate(user))


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """REQ-6.9 / SEC-DATA-005: delete the account, its records and its files."""
    doctor = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if doctor is not None:
        has_patients = db.query(Appointment.id).filter(Appointment.doctor_id == doctor.id).first()
        if has_patients:
            # Patients keep their consultation history and prescriptions.
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A doctor account with appointments cannot be deleted here. "
                "Please ask the clinic administrator to close it.",
            )
        db.delete(doctor)

    file_refs = collect_user_file_refs(current_user)

    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == current_user.id).delete(
        synchronize_session=False
    )
    db.delete(current_user)
    db.commit()

    remove_files(file_refs)
