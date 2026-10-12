
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
)
from app.utils.activity import create_task_activity
from app.utils.audit import create_audit_log
from app.utils.notification import create_notification


router = APIRouter(
    prefix="/tasks",
    tags=["Comments"],
)


# =========================================================
# HELPER: CHECK TASK ACCESS
# =========================================================

def check_task_access(
    task: Task,
    current_user: User,
) -> None:
    """Check whether the current user can access the task."""

    if current_user.role == "admin":
        return

    if current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task",
            )

        return

    if task.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task",
        )


# =========================================================
# HELPER: NOTIFY TASK PARTICIPANTS
# =========================================================

def notify_task_participants(
    db: Session,
    task: Task,
    current_user: User,
    visibility: str,
    comment_id: int,
) -> None:
    """
    Notify task participants about a new comment.

    Internal comments are not announced to employees who
    cannot view internal comments.
    """

    participant_ids = {
        task.created_by,
        task.assigned_to,
    }

    participant_ids.discard(None)
    participant_ids.discard(current_user.id)

    if not participant_ids:
        return

    participants = (
        db.query(User)
        .filter(User.id.in_(participant_ids))
        .all()
    )

    for participant in participants:
        # Employees cannot view internal comments.
        if (
            visibility == "internal"
            and participant.role == "employee"
        ):
            continue

        message = (
            f"New {visibility} comment on task "
            f"#{task.id} '{task.title}' "
            f"by {current_user.email}."
        )

        # Avoid creating the same notification more than once
        # for this comment and participant.
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == participant.id,
                Notification.message == message,
            )
            .first()
        )

        if existing is None:
            create_notification(
                db=db,
                user_id=participant.id,
                message=message,
            )


# =========================================================
# CREATE COMMENT
# =========================================================

@router.post(
    "/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    task_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    check_task_access(
        task=task,
        current_user=current_user,
    )

    # Employees cannot create internal comments.
    if (
        comment_data.visibility == "internal"
        and current_user.role == "employee"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot create internal comments",
        )

    new_comment = Comment(
        task_id=task.id,
        user_id=current_user.id,
        content=comment_data.content,
        visibility=comment_data.visibility,
    )

    db.add(new_comment)
    db.flush()

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="comment_added",
        details=(
            f"{comment_data.visibility.capitalize()} comment "
            f"added to task"
        ),
    )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="COMMENT_CREATED",
        entity="comment",
        entity_id=new_comment.id,
    )

    # Notify eligible participants about the new comment.
    notify_task_participants(
        db=db,
        task=task,
        current_user=current_user,
        visibility=comment_data.visibility,
        comment_id=new_comment.id,
    )

    db.commit()
    db.refresh(new_comment)

    return {
        "id": new_comment.id,
        "task_id": new_comment.task_id,
        "user_id": new_comment.user_id,
        "user_email": current_user.email,
        "content": new_comment.content,
        "visibility": new_comment.visibility,
        "created_at": new_comment.created_at,
        "updated_at": new_comment.updated_at,
    }


# =========================================================
# GET COMMENTS
# =========================================================

@router.get(
    "/{task_id}/comments",
    response_model=list[CommentResponse],
)
def get_comments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    check_task_access(
        task=task,
        current_user=current_user,
    )

    query = (
        db.query(
            Comment,
            User.email.label("user_email"),
        )
        .join(
            User,
            Comment.user_id == User.id,
        )
        .filter(
            Comment.task_id == task_id
        )
    )

    # Employees can see public comments only.
    if current_user.role == "employee":
        query = query.filter(
            Comment.visibility == "public"
        )

    comments = (
        query
        .order_by(Comment.created_at.asc())
        .all()
    )

    return [
        {
            "id": comment.id,
            "task_id": comment.task_id,
            "user_id": comment.user_id,
            "user_email": user_email,
            "content": comment.content,
            "visibility": comment.visibility,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
        }
        for comment, user_email in comments
    ]


# =========================================================
# UPDATE COMMENT
# =========================================================

@router.put(
    "/{task_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    task_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    check_task_access(
        task=task,
        current_user=current_user,
    )

    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.task_id == task_id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Only the comment author or an admin can edit it.
    if (
        comment.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own comments",
        )

    comment.content = comment_data.content

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="comment_updated",
        details=f"Comment ID {comment.id} was updated",
    )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="COMMENT_UPDATED",
        entity="comment",
        entity_id=comment.id,
    )

    db.commit()
    db.refresh(comment)

    comment_author_email = (
        db.query(User.email)
        .filter(User.id == comment.user_id)
        .scalar()
    )

    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "user_email": comment_author_email,
        "content": comment.content,
        "visibility": comment.visibility,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


# =========================================================
# DELETE COMMENT
# =========================================================

@router.delete(
    "/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    task_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    check_task_access(
        task=task,
        current_user=current_user,
    )

    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.task_id == task_id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Only the comment author or an admin can delete it.
    if (
        comment.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="comment_deleted",
        details=f"Comment ID {comment.id} was deleted",
    )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="COMMENT_DELETED",
        entity="comment",
        entity_id=comment.id,
    )

    db.delete(comment)
    db.commit()
