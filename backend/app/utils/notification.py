from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        message=message,
        is_read=False,
    )

    db.add(notification)

    return notification