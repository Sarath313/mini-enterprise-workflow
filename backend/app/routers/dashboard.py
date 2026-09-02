from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import DashboardResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/",
    response_model=DashboardResponse,
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Determine which tasks the current user is allowed to see.
    if current_user.role == "admin":
        query = db.query(Task)

    elif current_user.role == "manager":
        query = db.query(Task).filter(
            (Task.created_by == current_user.id)
            | (Task.assigned_to == current_user.id)
        )

    else:
        query = db.query(Task).filter(
            Task.assigned_to == current_user.id
        )

    tasks = query.all()

    total_tasks = len(tasks)

    todo_tasks = sum(
        1 for task in tasks
        if task.status == "todo"
    )

    in_progress_tasks = sum(
        1 for task in tasks
        if task.status == "in_progress"
    )

    done_tasks = sum(
        1 for task in tasks
        if task.status == "done"
    )

    low_priority_tasks = sum(
        1 for task in tasks
        if task.priority == "low"
    )

    medium_priority_tasks = sum(
        1 for task in tasks
        if task.priority == "medium"
    )

    high_priority_tasks = sum(
        1 for task in tasks
        if task.priority == "high"
    )

    assigned_tasks = sum(
        1 for task in tasks
        if task.assigned_to is not None
    )

    unassigned_tasks = sum(
        1 for task in tasks
        if task.assigned_to is None
    )

    now = datetime.utcnow()

    overdue_tasks = sum(
        1 for task in tasks
        if (
            task.due_date is not None
            and task.due_date < now
            and task.status != "done"
        )
    )

    return DashboardResponse(
        total_tasks=total_tasks,
        todo_tasks=todo_tasks,
        in_progress_tasks=in_progress_tasks,
        done_tasks=done_tasks,
        low_priority_tasks=low_priority_tasks,
        medium_priority_tasks=medium_priority_tasks,
        high_priority_tasks=high_priority_tasks,
        assigned_tasks=assigned_tasks,
        unassigned_tasks=unassigned_tasks,
        overdue_tasks=overdue_tasks,
    )