
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
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
    """
    Return task statistics for tasks the current user can access.
    """

    # ---------------------------------------------------------
    # ROLE-BASED TASK VISIBILITY
    # ---------------------------------------------------------

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

    # Task.due_date uses a timezone-naive DateTime column.
    # Use naive UTC to match the existing model convention.
    now = datetime.utcnow()

    # ---------------------------------------------------------
    # AGGREGATE DASHBOARD STATISTICS IN THE DATABASE
    # ---------------------------------------------------------

    statistics = query.with_entities(
        func.count(Task.id).label("total_tasks"),

        func.sum(
            case((Task.status == "todo", 1), else_=0)
        ).label("todo_tasks"),

        func.sum(
            case((Task.status == "in_progress", 1), else_=0)
        ).label("in_progress_tasks"),

        func.sum(
            case((Task.status == "done", 1), else_=0)
        ).label("done_tasks"),

        func.sum(
            case((Task.priority == "low", 1), else_=0)
        ).label("low_priority_tasks"),

        func.sum(
            case((Task.priority == "medium", 1), else_=0)
        ).label("medium_priority_tasks"),

        func.sum(
            case((Task.priority == "high", 1), else_=0)
        ).label("high_priority_tasks"),

        func.sum(
            case(
                (Task.assigned_to.isnot(None), 1),
                else_=0,
            )
        ).label("assigned_tasks"),

        func.sum(
            case(
                (Task.assigned_to.is_(None), 1),
                else_=0,
            )
        ).label("unassigned_tasks"),

        func.sum(
            case(
                (
                    (Task.due_date.isnot(None))
                    & (Task.due_date < now)
                    & (Task.status != "done"),
                    1,
                ),
                else_=0,
            )
        ).label("overdue_tasks"),
    ).one()

    # ---------------------------------------------------------
    # BUILD RESPONSE
    # ---------------------------------------------------------

    return DashboardResponse(
        total_tasks=statistics.total_tasks or 0,
        todo_tasks=statistics.todo_tasks or 0,
        in_progress_tasks=statistics.in_progress_tasks or 0,
        done_tasks=statistics.done_tasks or 0,
        low_priority_tasks=statistics.low_priority_tasks or 0,
        medium_priority_tasks=statistics.medium_priority_tasks or 0,
        high_priority_tasks=statistics.high_priority_tasks or 0,
        assigned_tasks=statistics.assigned_tasks or 0,
        unassigned_tasks=statistics.unassigned_tasks or 0,
        overdue_tasks=statistics.overdue_tasks or 0,
    )
