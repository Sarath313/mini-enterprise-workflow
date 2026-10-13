
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.password_reset import (
    generate_password_reset_token,
    hash_password_reset_token,
)
from app.core.password_reset_delivery import deliver_password_reset_token
from app.core.rate_limit import rate_limit
from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db, settings
from app.dependencies.auth import get_current_user
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def _csrf_token_signature(nonce: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _create_csrf_token() -> str:
    nonce = secrets.token_urlsafe(32)
    return f"{nonce}.{_csrf_token_signature(nonce)}"


def _valid_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token or not hmac.compare_digest(
        cookie_token, header_token
    ):
        return False
    try:
        nonce, signature = cookie_token.rsplit(".", 1)
    except ValueError:
        return False
    return bool(nonce) and hmac.compare_digest(
        signature, _csrf_token_signature(nonce)
    )


def _set_auth_cookies(response: Response, refresh_token: str) -> str:
    cookie_options = {
        "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "path": "/auth",
        "secure": settings.REFRESH_COOKIE_SECURE,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        **cookie_options,
    )
    csrf_token = _create_csrf_token()
    _set_csrf_cookie(response, csrf_token)
    return csrf_token


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    cookie_options = {
        "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "path": "/",
        "secure": settings.REFRESH_COOKIE_SECURE,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        httponly=True,
        **cookie_options,
    )


def _clear_auth_cookies(response: Response) -> None:
    cookie_options = {
        "path": "/auth",
        "secure": settings.REFRESH_COOKIE_SECURE,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        httponly=True,
        **cookie_options,
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        httponly=True,
        **{**cookie_options, "path": "/"},
    )


def _require_csrf(request: Request, header_token: str | None) -> None:
    if not _valid_csrf_token(
        request.cookies.get(CSRF_COOKIE_NAME),
        header_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


def _invalid_refresh_response(response: Response) -> JSONResponse:
    _clear_auth_cookies(response)
    error_response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired refresh token"},
    )
    error_response.raw_headers.extend(
        header for header in response.raw_headers if header[0] == b"set-cookie"
    )
    return error_response


@router.get("/csrf")
def get_csrf_token(response: Response):
    csrf_token = _create_csrf_token()
    _set_csrf_cookie(response, csrf_token)
    return {"csrf_token": csrf_token}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


def create_refresh_token_record(db: Session, user_id: int) -> str:
    raw_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=expires_at,
        )
    )
    return raw_token


def create_user_access_token(user: User) -> str:
    return create_access_token(
        data={"sub": str(user.id), "role": user.role},
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    email = str(user_data.email).strip().lower()

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        name=user_data.name,
        email=email,
        hashed_password=hash_password(user_data.password),
        role="employee",
        is_active=True,
    )

    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return new_user


@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(
        rate_limit(
            "login",
            lambda: settings.LOGIN_RATE_LIMIT_REQUESTS,
            lambda: settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
    ),
):
    email = form_data.username.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_user_access_token(user)
    refresh_token = create_refresh_token_record(db, user.id)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    csrf_token = _set_auth_cookies(response, refresh_token)

    return {
        "access_token": access_token,
        "csrf_token": csrf_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh(
    request: Request,
    response: Response,
    csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        return _invalid_refresh_response(response)
    _require_csrf(request, csrf_token)
    try:
        rotated = rotate_refresh_token(raw_refresh_token, db)
    except HTTPException:
        return _invalid_refresh_response(response)

    csrf_token = _set_auth_cookies(response, rotated["refresh_token"])
    return {
        "access_token": rotated["access_token"],
        "csrf_token": csrf_token,
        "token_type": "bearer",
    }


def rotate_refresh_token(raw_refresh_token: str, db: Session) -> dict[str, str]:
    token_hash = hash_refresh_token(raw_refresh_token)

    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )

    now = datetime.now(timezone.utc)

    if not record or record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        record.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = (
        db.query(User)
        .filter(User.id == record.user_id)
        .first()
    )

    if not user or not user.is_active:
        record.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    record.revoked_at = now
    new_refresh_token = create_refresh_token_record(db, user.id)
    access_token = create_user_access_token(user)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    db: Session = Depends(get_db),
):
    _require_csrf(request, csrf_token)
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        _clear_auth_cookies(response)
        return {"message": "Logged out"}

    revoke_refresh_token(raw_refresh_token, db)
    _clear_auth_cookies(response)
    return {"message": "Logged out"}


def revoke_refresh_token(raw_refresh_token: str, db: Session) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)

    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(
        rate_limit(
            "forgot-password",
            lambda: settings.FORGOT_PASSWORD_RATE_LIMIT_REQUESTS,
            lambda: settings.FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
        )
    ),
):
    generic_response = {
        "message": (
            "If the account exists and email delivery is configured, "
            "password reset instructions will be sent."
        )
    }

    email = str(request.email).strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or not user.is_active:
        return generic_response

    now = datetime.now(timezone.utc)

    # Invalidate previously issued, unused reset tokens.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update(
        {PasswordResetToken.used_at: now},
        synchronize_session=False,
    )

    raw_token = generate_password_reset_token()

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=now + timedelta(
                minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            ),
        )
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Never return the reset token in the public API response.
    deliver_password_reset_token(user.email, raw_token)

    return generic_response


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(
        rate_limit(
            "reset-password",
            lambda: settings.RESET_PASSWORD_RATE_LIMIT_REQUESTS,
            lambda: settings.RESET_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
        )
    ),
):
    now = datetime.now(timezone.utc)
    token_hash = hash_password_reset_token(request.token)

    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )

    if not record or record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user = (
        db.query(User)
        .filter(User.id == record.user_id)
        .with_for_update()
        .first()
    )

    if not user or not user.is_active:
        record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user.hashed_password = hash_password(request.new_password)
    record.used_at = now

    # Revoke all active refresh tokens after a password change.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update(
        {RefreshToken.revoked_at: now},
        synchronize_session=False,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "Password reset successful"}


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
