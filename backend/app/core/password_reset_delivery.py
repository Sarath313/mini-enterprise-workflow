import os
from pathlib import Path

from app.database import settings


def deliver_password_reset_token(email: str, token: str) -> None:
    """Write a reset link locally only when explicitly enabled for development."""
    mode = settings.PASSWORD_RESET_DELIVERY_MODE

    if mode == "disabled":
        return

    if mode != "development_file":
        raise RuntimeError("Unsupported password reset delivery mode")

    if os.getenv("APP_ENV", "").lower() != "development":
        raise RuntimeError(
            "Development file delivery requires APP_ENV=development"
        )

    output_dir = Path(".dev-reset-links")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Use a fixed filename and restrictive permissions.
    # Do not include email addresses or tokens in log output.
    output_file = output_dir / "latest-reset-link.txt"
    link = f"Password reset token: {token}\n"

    fd = os.open(
        output_file,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(link)
