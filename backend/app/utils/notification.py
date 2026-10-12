
from sqlalchemy.orm import Session

from app.models.notification import Notification


MAX_NOTIFICATION_LENGTH = 500


def create_notification(
    db: Session,
    user_id: int,
    message: str,
) -> Notification:
    normalized_message = message.strip()

    if not normalized_message:
        raise ValueError("Notification message cannot be empty")

    if len(normalized_message) > MAX_NOTIFICATION_LENGTH:
        normalized_message = normalized_message[:MAX_NOTIFICATION_LENGTH]

    notification = Notification(
        user_id=user_id,
        message=normalized_message,
        is_read=False,
    )

    db.add(notification)

    return notification
