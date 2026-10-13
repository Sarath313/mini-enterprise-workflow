
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_admin,
)
from app.models.user import User
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# =========================================================
# GET USERS (ADMIN ONLY)
# =========================================================

@router.get(
    "/",
    response_model=list[UserResponse],
)
def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    role: Literal["admin", "manager", "employee"] | None = Query(
        default=None
    ),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: Literal["id", "name", "email", "created_at"] = Query(
        default="id"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of users.
    Only administrators can access this endpoint.
    """

    query = db.query(User)
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    if search is not None:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    sort_column = {
        "id": User.id,
        "name": User.name,
        "email": User.email,
        "created_at": User.created_at,
    }[sort_by]
    order = desc if sort_order == "desc" else asc
    ordering = [order(sort_column)]
    if sort_by != "id":
        ordering.append(order(User.id))

    return (
        query
        .order_by(*ordering)
        .offset(skip)
        .limit(limit)
        .all()
    )


# =========================================================
# GET USER BY ID
# =========================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a user by ID.

    Any authenticated user can access this endpoint,
    matching the existing application permissions.
    """

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
