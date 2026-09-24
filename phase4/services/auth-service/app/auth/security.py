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


def get_signing_key(token: str) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        )

    jwks = get_jwks()

    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find token signing key",
    )


def validate_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    settings = get_settings()

    token = credentials.credentials
    signing_key = get_signing_key(token)

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )