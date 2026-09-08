from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
)
from app.utils.activity import create_task_activity


router = APIRouter(
    prefix="/tasks",
    tags=["Comments"],
)


# =========================================================
# HELPER — CHECK TASK ACCESS
# =========================================================

def check_task_access(
    task: Task,
    current_user: User,
) -> None:
    """
    Check whether the current user can access the task.
    """

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

    # ---------------------------------------------------------
    # CHECK TASK ACCESS
    # ---------------------------------------------------------

    check_task_access(
        task=task,
        current_user=current_user,
    )

    # ---------------------------------------------------------
    # INTERNAL COMMENT RESTRICTION
    # ---------------------------------------------------------

    if (
        comment_data.visibility == "internal"
        and current_user.role == "employee"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot create internal comments",
        )

    # ---------------------------------------------------------
    # CREATE COMMENT
    # ---------------------------------------------------------

    new_comment = Comment(
        task_id=task.id,
        user_id=current_user.id,
        content=comment_data.content,
        visibility=comment_data.visibility,
    )

    db.add(new_comment)
    db.flush()

    # ---------------------------------------------------------
    # ACTIVITY LOG
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # CHECK TASK ACCESS
    # ---------------------------------------------------------

    check_task_access(
        task=task,
        current_user=current_user,
    )

    # ---------------------------------------------------------
    # GET COMMENTS
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # INTERNAL COMMENTS
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # COMMENT OWNERSHIP
    # ---------------------------------------------------------

    if (
        comment.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own comments",
        )

    # ---------------------------------------------------------
    # UPDATE COMMENT
    # ---------------------------------------------------------

    comment.content = comment_data.content

    # ---------------------------------------------------------
    # ACTIVITY LOG
    # ---------------------------------------------------------

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="comment_updated",
        details=f"Comment ID {comment.id} was updated",
    )

    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "user_email": (
            current_user.email
            if comment.user_id == current_user.id
            else db.query(User.email)
            .filter(User.id == comment.user_id)
            .scalar()
        ),
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

    # ---------------------------------------------------------
    # COMMENT OWNERSHIP
    # ---------------------------------------------------------

    if (
        comment.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    # ---------------------------------------------------------
    # ACTIVITY LOG
    # ---------------------------------------------------------

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="comment_deleted",
        details=f"Comment ID {comment.id} was deleted",
    )

    db.delete(comment)

    db.commit()