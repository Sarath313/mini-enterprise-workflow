
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db, settings
from app.dependencies.auth import get_current_user
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str


def create_refresh_token_record(db: Session, user_id: int) -> str:
    raw_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=expires_at,
    )
    db.add(record)
    return raw_token


def create_user_access_token(user: User) -> str:
    return create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=60),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User).filter(User.email == user_data.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User).filter(User.email == form_data.username).first()
    )

    if not user or not verify_password(
        form_data.password, user.hashed_password
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
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(request.refresh_token)
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

    # Rotate the token: the old token cannot be reused.
    record.revoked_at = now
    new_refresh_token = create_refresh_token_record(db, user.id)
    access_token = create_user_access_token(user)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(request.refresh_token)
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()

    # Idempotent response: don't reveal whether a token existed.
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
