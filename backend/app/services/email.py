"""
Transactional e-mail (password reset).

Uses SMTP when SMTP_HOST and SMTP_FROM are configured. In development
without SMTP, the reset link is written to the server log (never to the API
response). In production without SMTP, password reset is disabled by the
router before this module is reached.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from contextlib import contextmanager
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("skyntri.email")


class EmailDeliveryError(RuntimeError):
    pass


@contextmanager
def open_server():
    """Connect to the configured mail server and log in. Raises OSError / SMTPException."""
    if settings.smtp_port == 465:
        server = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            context=ssl.create_default_context(),
            timeout=15,
        )
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)

    with server:
        if settings.smtp_port != 465 and settings.smtp_use_tls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        yield server


def _send(message: EmailMessage) -> None:
    try:
        with open_server() as server:
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("E-mail could not be sent") from exc


def send_password_reset_email(to_email: str, full_name: str, reset_link: str) -> None:
    minutes = settings.password_reset_token_minutes

    if not settings.smtp_configured:
        if not settings.is_production and settings.dev_log_reset_links:
            logger.warning(
                "DEVELOPMENT ONLY - SMTP is not configured. Password reset link for %s: %s",
                to_email,
                reset_link,
            )
        return

    message = EmailMessage()
    message["Subject"] = "Reset your Skyntri password"
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(
        f"Hello {full_name or 'there'},\n\n"
        "We received a request to reset your Skyntri password.\n"
        f"Use this link within {minutes} minutes. It can only be used once:\n\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this e-mail; your password "
        "will not change.\n\n- Skyntri"
    )

    _send(message)
