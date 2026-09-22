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
from app.utils.audit import create_audit_log


router = APIRouter(
    prefix="/tasks",
    tags=["Approvals"],
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
# HELPER — BUILD APPROVAL RESPONSE
# =========================================================

def build_approval_response(
    approval: Approval,
) -> ApprovalResponse:
    """
    Convert an Approval model into the API response schema.
    """

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


# =========================================================
# SUBMIT FOR APPROVAL
# =========================================================

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
    """
    Submit a task in review status for manager approval.
    """

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

    check_task_access(
        task,
        current_user,
    )

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
        .filter(
            User.role == "manager",
            User.id != current_user.id,
        )
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

    # ---------------------------------------------------------
    # PHASE 3 AUDIT LOG
    # ---------------------------------------------------------

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="APPROVAL_CREATED",
        entity="approval",
        entity_id=approval.id,
    )

    db.commit()
    db.refresh(approval)

    return build_approval_response(approval)


# =========================================================
# GET TASK APPROVALS
# =========================================================

@router.get(
    "/{task_id}/approvals",
    response_model=list[ApprovalResponse],
)
def get_task_approvals(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all approval records associated with a task.
    """

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

    check_task_access(
        task,
        current_user,
    )

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


# =========================================================
# GET APPROVAL HISTORY
# =========================================================

@router.get(
    "/{task_id}/approvals/history",
    response_model=list[ApprovalHistoryResponse],
)
def get_approval_history(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the complete approval audit history for a task.
    """

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

    check_task_access(
        task,
        current_user,
    )

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


# =========================================================
# PROCESS APPROVAL
# =========================================================

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
    """
    Approve, reject, or hold an approval.
    """

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

    # ---------------------------------------------------------
    # ROLE CHECK
    # ---------------------------------------------------------

    if current_user.role not in {
        "manager",
        "admin",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only managers and admins "
                "can process approvals"
            ),
        )

    # ---------------------------------------------------------
    # APPROVER CHECK
    # ---------------------------------------------------------

    if approval.approver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned approver",
        )

    # ---------------------------------------------------------
    # APPROVAL LEVEL CHECK
    # ---------------------------------------------------------

    if (
        approval.level == "manager"
        and current_user.role != "manager"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only a manager can process "
                "manager-level approval"
            ),
        )

    if (
        approval.level == "admin"
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only an admin can process "
                "admin-level approval"
            ),
        )

    # ---------------------------------------------------------
    # STATUS CHECK
    # ---------------------------------------------------------

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been processed",
        )

    if approval_data.action == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Submitted is not a valid "
                "approval decision"
            ),
        )

    # ---------------------------------------------------------
    # REJECTION COMMENT VALIDATION
    # ---------------------------------------------------------

    if approval_data.action == "rejected":
        if (
            not approval_data.comment
            or not approval_data.comment.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A comment is required "
                    "when rejecting an approval"
                ),
            )

    # ---------------------------------------------------------
    # UPDATE APPROVAL
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # PHASE 3 AUDIT LOG — APPROVAL PROCESSED
    # ---------------------------------------------------------

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="APPROVAL_PROCESSED",
        entity="approval",
        entity_id=approval.id,
    )

    # ---------------------------------------------------------
    # REJECT
    # ---------------------------------------------------------

    if approval_data.action == "rejected":
        old_status = task.status
        task.status = "in_progress"

        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="approval_rejected",
            details=(
                f"{approval.level.title()} approval "
                f"rejected. Task returned to in_progress."
            ),
        )

        if old_status != task.status:
            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_STATUS_CHANGED",
                entity="task",
                entity_id=task.id,
            )

    # ---------------------------------------------------------
    # HOLD
    # ---------------------------------------------------------

    elif approval_data.action == "hold":
        old_status = task.status
        task.status = "review"

        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="approval_on_hold",
            details=(
                f"{approval.level.title()} approval "
                f"placed on hold."
            ),
        )

        if old_status != task.status:
            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_STATUS_CHANGED",
                entity="task",
                entity_id=task.id,
            )

    # ---------------------------------------------------------
    # MANAGER APPROVED → ESCALATE TO ADMIN
    # ---------------------------------------------------------

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
                detail=(
                    "No admin is available "
                    "for final approval"
                ),
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
                "Manager approval completed. "
                f"Task escalated to admin {admin.id} "
                "for final approval."
            ),
        )

        # -----------------------------------------------------
        # PHASE 3 AUDIT LOG — ESCALATION
        # -----------------------------------------------------

        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="APPROVAL_ESCALATED",
            entity="approval",
            entity_id=admin_approval.id,
        )

        # Task remains in review while waiting
        # for final admin approval.
        old_status = task.status
        task.status = "review"

        if old_status != task.status:
            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_STATUS_CHANGED",
                entity="task",
                entity_id=task.id,
            )

    # ---------------------------------------------------------
    # ADMIN APPROVED → COMPLETE TASK
    # ---------------------------------------------------------

    elif (
        approval_data.action == "approved"
        and approval.level == "admin"
    ):
        old_status = task.status
        task.status = "done"

        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="task_completed",
            details=(
                "Final admin approval completed. "
                "Task marked as done."
            ),
        )

        if old_status != task.status:
            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_STATUS_CHANGED",
                entity="task",
                entity_id=task.id,
            )

    # ---------------------------------------------------------
    # COMMIT
    # ---------------------------------------------------------

    db.commit()
    db.refresh(approval)

    return build_approval_response(approval)