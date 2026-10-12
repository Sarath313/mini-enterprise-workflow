from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)


def generate_password_reset_token() -> str:
    """Generate a cryptographically secure reset token."""
    return generate_refresh_token()


def hash_password_reset_token(token: str) -> str:
    """Hash a reset token before storing it."""
    return hash_refresh_token(token)
