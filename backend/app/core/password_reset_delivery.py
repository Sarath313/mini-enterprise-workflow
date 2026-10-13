import os
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

from app.database import settings


logger = logging.getLogger(__name__)


def _send_smtp_reset_email(email: str, token: str) -> None:
    required_settings = (
        settings.SMTP_HOST,
        settings.SMTP_FROM_EMAIL,
        settings.PASSWORD_RESET_FRONTEND_URL,
    )
    if not all(required_settings):
        logger.warning(
            "Password-reset email delivery is disabled: SMTP is not fully configured"
        )
        return
    if bool(settings.SMTP_USERNAME) != bool(settings.SMTP_PASSWORD):
        logger.warning(
            "Password-reset email delivery is disabled: SMTP credentials are incomplete"
        )
        return

    reset_url = (
        f"{settings.PASSWORD_RESET_FRONTEND_URL.rstrip('/')}"
        f"/reset-password#token={quote(token, safe='')}"
    )
    message = EmailMessage()
    message["Subject"] = "Reset your Mini Enterprise Workflow password"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message.set_content(
        "A password reset was requested for your account.\n\n"
        f"Use this link to choose a new password: {reset_url}\n\n"
        f"This link expires in "
        f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. "
        "If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as server:
            if settings.SMTP_STARTTLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        logger.error(
            "Password-reset email delivery failed (%s)",
            type(error).__name__,
        )


def deliver_password_reset_token(email: str, token: str) -> None:
    """Deliver a reset link through an explicitly configured provider."""
    mode = settings.PASSWORD_RESET_DELIVERY_MODE

    if mode == "disabled":
        return

    if mode == "smtp":
        _send_smtp_reset_email(email, token)
        return

    if mode != "development_file":
        raise RuntimeError("Unsupported password reset delivery mode")

    if settings.APP_ENV.lower() != "development":
        raise RuntimeError(
            "Development file delivery requires APP_ENV=development"
        )

    output_dir = Path(".dev-reset-links")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Use a fixed filename and restrictive permissions.
    # Do not include email addresses or tokens in log output.
    output_file = output_dir / "latest-reset-link.txt"
    frontend_url = settings.PASSWORD_RESET_FRONTEND_URL
    if not frontend_url and settings.APP_ENV.lower() == "development":
        frontend_url = "http://localhost:5173"
    if not frontend_url:
        logger.warning(
            "Development password-reset link was not written: frontend URL is not configured"
        )
        return
    reset_url = (
        f"{frontend_url.rstrip('/')}"
        f"/reset-password#token={quote(token, safe='')}"
    )
    link = f"Password reset link: {reset_url}\n"

    fd = os.open(
        output_file,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(link)
