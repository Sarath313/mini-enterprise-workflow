from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_auth0_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import (
    create_or_update_user,
    get_user_by_auth0_id,
    get_user_by_id,
    update_user,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    auth0_user: dict = Depends(get_current_auth0_user),
):
    if user_data.auth0_user_id != auth0_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User identity does not match access token",
        )

    return create_or_update_user(
        db,
        user_data,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    db: Session = Depends(get_db),
    auth0_user: dict = Depends(get_current_auth0_user),
):
    auth0_user_id = auth0_user.get("sub")

    user = get_user_by_auth0_id(
        db,
        auth0_user_id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    auth0_user: dict = Depends(get_current_auth0_user),
):
    current_user = get_user_by_auth0_id(
        db,
        auth0_user.get("sub"),
    )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user not found",
        )

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile",
        )

    user = get_user_by_id(
        db,
        user_id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user_profile(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    auth0_user: dict = Depends(get_current_auth0_user),
):
    current_user = get_user_by_auth0_id(
        db,
        auth0_user.get("sub"),
    )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user not found",
        )

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile",
        )

    return update_user(
        db,
        current_user,
        user_data,
    )