from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings


security = HTTPBearer()


@lru_cache
def get_jwks() -> dict:
    settings = get_settings()

    response = httpx.get(
        f"https://{settings.auth0_domain}/.well-known/jwks.json",
        timeout=10.0,
    )

    response.raise_for_status()

    return response.json()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    settings = get_settings()

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    signing_key = None

    for key in get_jwks().get("keys", []):
        if key.get("kid") == header.get("kid"):
            signing_key = key
            break

    if not signing_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signing key not found",
        )

    try:
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )