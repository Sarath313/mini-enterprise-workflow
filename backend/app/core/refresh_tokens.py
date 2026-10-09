import hashlib
import secrets


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest of a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
