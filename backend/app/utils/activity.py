from sqlalchemy.orm import Session

from app.models.activity import TaskActivity


def create_task_activity(
    db: Session,
    task_id: int,
    user_id: int,
    action: str,
    details: str | None = None,
):
    activity = TaskActivity(
        task_id=task_id,
        user_id=user_id,
        action=action,
        details=details,
    )

    db.add(activity)

    return activity