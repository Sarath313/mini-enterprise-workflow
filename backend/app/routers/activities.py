from fastapi import APIRouter, Depends, HTTPException, status
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is not None:
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
        .order_by(TaskActivity.created_at.asc())
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