
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


# =========================================================
# GET NOTIFICATIONS
# =========================================================

@router.get(
    "/",
    response_model=list[NotificationResponse],
)
def get_notifications(
    unread_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    sort_by: Literal["created_at", "id"] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return notifications belonging only to the current user.

    Supports unread filtering and pagination.
    """

    query = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
    )

    if unread_only:
        query = query.filter(
            Notification.is_read.is_(False)
        )

    order = desc if sort_order == "desc" else asc
    sort_column = {
        "created_at": Notification.created_at,
        "id": Notification.id,
    }[sort_by]
    ordering = [order(sort_column)]
    if sort_by != "id":
        ordering.append(order(Notification.id))
    return (
        query
        .order_by(*ordering)
        .offset(skip)
        .limit(limit)
        .all()
    )


# =========================================================
# MARK NOTIFICATION AS READ
# =========================================================

@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a notification as read.

    Users can only modify their own notifications.
    """

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification
