from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.approval import Approval
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.utils.notification import create_notification


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


def sync_notifications(
    db: Session,
    current_user: User,
) -> None:
    """
    Create missing user-specific notifications.

    This keeps notification generation independent from
    the task and approval routers.
    """

    # ---------------------------------------------------------
    # Pending approvals assigned to current user
    # ---------------------------------------------------------

    pending_approvals = (
        db.query(Approval)
        .filter(
            Approval.approver_id == current_user.id,
            Approval.status == "pending",
        )
        .all()
    )

    for approval in pending_approvals:
        message = (
            f"Approval #{approval.id} for Task "
            f"#{approval.task_id} is waiting for your action."
        )

        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == current_user.id,
                Notification.message == message,
            )
            .first()
        )

        if existing is None:
            create_notification(
                db=db,
                user_id=current_user.id,
                message=message,
            )

    # ---------------------------------------------------------
    # Tasks assigned to current user
    # ---------------------------------------------------------

    assigned_tasks = (
        db.query(Task)
        .filter(
            Task.assigned_to == current_user.id,
            Task.status.notin_(["done"]),
        )
        .all()
    )

    for task in assigned_tasks:
        message = (
            f"Task #{task.id} '{task.title}' "
            f"is assigned to you."
        )

        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == current_user.id,
                Notification.message == message,
            )
            .first()
        )

        if existing is None:
            create_notification(
                db=db,
                user_id=current_user.id,
                message=message,
            )

    db.commit()


@router.get(
    "/",
    response_model=list[NotificationResponse],
)
def get_notifications(
    unread_only: bool = Query(
        default=False,
    ),
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return notifications belonging only to the current user.
    """

    sync_notifications(
        db=db,
        current_user=current_user,
    )

    query = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
        )
    )

    if unread_only:
        query = query.filter(
            Notification.is_read.is_(False),
        )

    return (
        query
        .order_by(desc(Notification.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


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