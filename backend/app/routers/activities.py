
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.activity import TaskActivity
from app.models.task import Task
from app.models.user import User
from app.schemas.activity import ActivityResponse


router = APIRouter(
    prefix="/tasks",
    tags=["Task Activities"],
)


@router.get(
    "/{task_id}/activities",
    response_model=list[ActivityResponse],
)
def get_task_activities(
    task_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find the task first.
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Enforce task access permissions.
    if current_user.role == "admin":
        pass

    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task's activities",
            )

    else:
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task's activities",
            )

    # Retrieve activity history with the associated user's email.
    activities = (
        db.query(
            TaskActivity,
            User.email.label("user_email"),
        )
        .join(
            User,
            TaskActivity.user_id == User.id,
        )
        .filter(TaskActivity.task_id == task_id)
        .order_by(
            TaskActivity.created_at.asc(),
            TaskActivity.id.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": activity.id,
            "task_id": activity.task_id,
            "user_id": activity.user_id,
            "user_email": user_email,
            "action": activity.action,
            "details": activity.details,
            "created_at": activity.created_at,
        }
        for activity, user_email in activities
    ]
