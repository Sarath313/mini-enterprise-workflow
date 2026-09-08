from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.approval import Approval
from app.models.approval_history import ApprovalHistory
from app.models.task import Task
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalHistoryResponse,
    ApprovalResponse,
)
from app.utils.activity import create_task_activity


router = APIRouter(
    prefix="/tasks",
    tags=["Approvals"],
)


def check_task_access(
    task: Task,
    current_user: User,
) -> None:
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


def build_approval_response(
    approval: Approval,
) -> ApprovalResponse:
    return ApprovalResponse(
        id=approval.id,
        task_id=approval.task_id,
        requested_by=approval.requested_by,
        approver_id=approval.approver_id,
        level=approval.level,
        status=approval.status,
        comment=approval.comment,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )


@router.post(
    "/{task_id}/approvals",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_for_approval(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    check_task_access(task, current_user)

    if task.status != "review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only tasks in review status "
                "can be submitted for approval"
            ),
        )

    existing_approval = (
        db.query(Approval)
        .filter(
            Approval.task_id == task_id,
            Approval.status == "pending",
        )
        .first()
    )

    if existing_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task already has a pending approval",
        )

    manager = (
        db.query(User)
        .filter(User.role == "manager")
        .order_by(User.id)
        .first()
    )

    if not manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No manager is available for approval",
        )

    approval = Approval(
        task_id=task.id,
        requested_by=current_user.id,
        approver_id=manager.id,
        level="manager",
        status="pending",
    )

    db.add(approval)
    db.flush()

    history = ApprovalHistory(
        approval_id=approval.id,
        task_id=task.id,
        action_by=current_user.id,
        action="submitted",
    )

    db.add(history)

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="approval_submitted",
        details=(
            f"Task submitted for manager approval "
            f"to user {manager.id}"
        ),
    )

    db.commit()
    db.refresh(approval)

    return build_approval_response(approval)


@router.get(
    "/{task_id}/approvals",
    response_model=list[ApprovalResponse],
)
def get_task_approvals(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    check_task_access(task, current_user)

    approvals = (
        db.query(Approval)
        .filter(
            Approval.task_id == task_id
        )
        .order_by(
            Approval.created_at.asc()
        )
        .all()
    )

    return [
        build_approval_response(approval)
        for approval in approvals
    ]


@router.get(
    "/{task_id}/approvals/history",
    response_model=list[ApprovalHistoryResponse],
)
def get_approval_history(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    check_task_access(task, current_user)

    history = (
        db.query(ApprovalHistory)
        .filter(
            ApprovalHistory.task_id == task_id
        )
        .order_by(
            ApprovalHistory.created_at.asc()
        )
        .all()
    )

    return history


@router.patch(
    "/{task_id}/approvals/{approval_id}",
    response_model=ApprovalResponse,
)
def process_approval(
    task_id: int,
    approval_id: int,
    approval_data: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    approval = (
        db.query(Approval)
        .filter(
            Approval.id == approval_id,
            Approval.task_id == task_id,
        )
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )

    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can process approvals",
        )

    if approval.approver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned approver",
        )

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been processed",
        )

    if (
        approval_data.action == "rejected"
        and not approval_data.comment
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A comment is required when rejecting an approval",
        )

    if approval_data.action == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted is not a valid approval decision",
        )

    approval.status = approval_data.action
    approval.comment = approval_data.comment

    history = ApprovalHistory(
        approval_id=approval.id,
        task_id=task.id,
        action_by=current_user.id,
        action=approval_data.action,
        comment=approval_data.comment,
    )

    db.add(history)

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action=f"approval_{approval_data.action}",
        details=(
            f"{approval.level.title()} approval "
            f"{approval_data.action}."
        ),
    )

    # Rejection sends the task back for changes.
    if approval_data.action == "rejected":
        task.status = "in_progress"

    # Hold keeps the task in review.
    elif approval_data.action == "hold":
        task.status = "review"

    # Manager approval escalates to Admin.
    elif (
        approval_data.action == "approved"
        and approval.level == "manager"
    ):
        admin = (
            db.query(User)
            .filter(User.role == "admin")
            .order_by(User.id)
            .first()
        )

        if not admin:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No admin is available for final approval",
            )

        admin_approval = Approval(
            task_id=task.id,
            requested_by=current_user.id,
            approver_id=admin.id,
            level="admin",
            status="pending",
        )

        db.add(admin_approval)
        db.flush()

        admin_history = ApprovalHistory(
            approval_id=admin_approval.id,
            task_id=task.id,
            action_by=current_user.id,
            action="submitted",
        )

        db.add(admin_history)

        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="approval_escalated",
            details=(
                f"Manager approval completed. "
                f"Task escalated to admin {admin.id} "
                f"for final approval."
            ),
        )

    # Admin approval completes the workflow.
    elif (
        approval_data.action == "approved"
        and approval.level == "admin"
    ):
        task.status = "done"

        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="task_completed",
            details="Final admin approval completed.",
        )

    db.commit()
    db.refresh(approval)

    return build_approval_response(approval)