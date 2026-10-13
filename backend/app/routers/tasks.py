
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.dashboard_cache import invalidate_dashboard_cache
from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_manager_or_admin,
)
from app.models.status_history import TaskStatusHistory
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    KanbanResponse,
    TaskAssign,
    TaskCreate,
    TaskResponse,
    TaskPriority,
    TaskStatus,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.utils.activity import create_task_activity
from app.utils.audit import create_audit_log
from app.utils.notification import create_notification
from app.utils.workflow import validate_status_transition


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


# =========================================================
# CREATE TASK
# =========================================================

@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    if task_data.assigned_to is not None:
        assigned_user = (
            db.query(User)
            .filter(User.id == task_data.assigned_to)
            .first()
        )

        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        assigned_to=task_data.assigned_to,
        created_by=current_user.id,
    )

    db.add(new_task)
    db.flush()

    create_task_activity(
        db=db,
        task_id=new_task.id,
        user_id=current_user.id,
        action="created",
        details=f"Task '{new_task.title}' was created",
    )

    if new_task.assigned_to is not None:
        create_task_activity(
            db=db,
            task_id=new_task.id,
            user_id=current_user.id,
            action="assigned",
            details=(
                f"Task assigned to user ID "
                f"{new_task.assigned_to}"
            ),
        )

        create_notification(
            db=db,
            user_id=new_task.assigned_to,
            message=(
                f"You have been assigned task #{new_task.id}: "
                f"{new_task.title}."
            ),
        )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="TASK_CREATED",
        entity="task",
        entity_id=new_task.id,
    )

    db.commit()
    invalidate_dashboard_cache()
    db.refresh(new_task)

    return new_task


# =========================================================
# GET TASKS
# =========================================================

@router.get(
    "/",
    response_model=list[TaskResponse],
)
def get_tasks(
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    assigned_to: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: Literal[
        "created_at",
        "due_date",
        "title",
        "status",
        "priority",
    ] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    if status is not None:
        query = query.filter(Task.status == status)

    if priority is not None:
        query = query.filter(Task.priority == priority)

    if assigned_to is not None:
        query = query.filter(Task.assigned_to == assigned_to)

    sort_column = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "title": Task.title,
        "status": Task.status,
        "priority": Task.priority,
    }[sort_by]
    order = desc if sort_order == "desc" else asc
    tasks = (
        query
        .order_by(order(sort_column), order(Task.id))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return tasks


# =========================================================
# GET KANBAN BOARD
# =========================================================

@router.get(
    "/kanban",
    response_model=KanbanResponse,
)
def get_kanban_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    tasks = (
        query
        .order_by(Task.created_at.desc())
        .all()
    )

    kanban = {
        "todo": [],
        "in_progress": [],
        "review": [],
        "done": [],
    }

    for task in tasks:
        if task.status in kanban:
            kanban[task.status].append(task)

    return kanban


# =========================================================
# GET SINGLE TASK
# =========================================================

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
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

    if current_user.role == "admin":
        return task

    if current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task",
            )

        return task

    if task.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task",
        )

    return task


# =========================================================
# UPDATE TASK
# =========================================================

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
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

    # Role-based access control
    if current_user.role == "admin":
        pass

    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to update this task",
            )

    else:
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you",
            )

        if task_data.status is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update task status",
            )

        if (
            task_data.title is not None
            or task_data.description is not None
            or task_data.priority is not None
            or task_data.due_date is not None
            or task_data.assigned_to is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update task status",
            )

    update_data = task_data.model_dump(
        exclude_unset=True
    )

    # Validate new assignee
    if "assigned_to" in update_data:
        if update_data["assigned_to"] is not None:
            assigned_user = (
                db.query(User)
                .filter(User.id == update_data["assigned_to"])
                .first()
            )

            if assigned_user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned user not found",
                )

    old_status = task.status
    old_assigned_to = task.assigned_to

    # Validate status transition
    if "status" in update_data:
        validate_status_transition(
            current_status=old_status,
            new_status=update_data["status"],
        )

    # Apply updates
    for field, value in update_data.items():
        setattr(task, field, value)

    # Status activity, history and audit
    if "status" in update_data:
        if old_status != task.status:
            create_task_activity(
                db=db,
                task_id=task.id,
                user_id=current_user.id,
                action="status_changed",
                details=(
                    f"Status changed from '{old_status}' "
                    f"to '{task.status}'"
                ),
            )

            status_history = TaskStatusHistory(
                task_id=task.id,
                from_status=old_status,
                to_status=task.status,
                changed_by=current_user.id,
            )

            db.add(status_history)

            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_STATUS_CHANGED",
                entity="task",
                entity_id=task.id,
            )

    # Assignment activity, audit and notification
    if "assigned_to" in update_data:
        if old_assigned_to != task.assigned_to:
            if task.assigned_to is None:
                details = "Task assignment removed"
            else:
                details = (
                    f"Task assigned to user ID "
                    f"{task.assigned_to}"
                )

            create_task_activity(
                db=db,
                task_id=task.id,
                user_id=current_user.id,
                action="assigned",
                details=details,
            )

            create_audit_log(
                db=db,
                user_id=current_user.id,
                action="TASK_ASSIGNED",
                entity="task",
                entity_id=task.id,
            )

            if task.assigned_to is not None:
                create_notification(
                    db=db,
                    user_id=task.assigned_to,
                    message=(
                        f"You have been assigned task #{task.id}: "
                        f"{task.title}."
                    ),
                )

    # Other field update activity and audit
    non_activity_fields = {
        "status",
        "assigned_to",
    }

    other_changes = [
        field
        for field in update_data
        if field not in non_activity_fields
    ]

    if other_changes:
        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="updated",
            details=(
                "Updated fields: "
                + ", ".join(other_changes)
            ),
        )

        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="TASK_UPDATED",
            entity="task",
            entity_id=task.id,
        )

    db.commit()
    invalidate_dashboard_cache()
    db.refresh(task)

    return task


# =========================================================
# UPDATE TASK STATUS
# =========================================================

@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
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

    # Role-based access control
    if current_user.role == "admin":
        pass

    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to update this task",
            )

    else:
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you",
            )

    old_status = task.status
    new_status = status_data.status

    validate_status_transition(
        current_status=old_status,
        new_status=new_status,
    )

    if old_status == new_status:
        return task

    task.status = new_status

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="status_changed",
        details=(
            f"Status changed from '{old_status}' "
            f"to '{new_status}'"
        ),
    )

    status_history = TaskStatusHistory(
        task_id=task.id,
        from_status=old_status,
        to_status=new_status,
        changed_by=current_user.id,
    )

    db.add(status_history)

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="TASK_STATUS_CHANGED",
        entity="task",
        entity_id=task.id,
    )

    db.commit()
    invalidate_dashboard_cache()
    db.refresh(task)

    return task


# =========================================================
# DELETE TASK
# =========================================================

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
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

    # Role-based access control
    if current_user.role == "admin":
        pass

    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this task",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot delete tasks",
        )

    create_task_activity(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        action="deleted",
        details=f"Task '{task.title}' was deleted",
    )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="TASK_DELETED",
        entity="task",
        entity_id=task.id,
    )

    db.flush()

    db.delete(task)

    db.commit()
    invalidate_dashboard_cache()


# =========================================================
# ASSIGN TASK
# =========================================================

@router.patch(
    "/{task_id}/assign",
    response_model=TaskResponse,
)
def assign_task(
    task_id: int,
    assignment: TaskAssign,
    current_user: User = Depends(require_manager_or_admin),
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

    # Managers can only assign tasks they created
    if current_user.role == "manager":
        if task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign tasks they created",
            )

    # Validate assignee
    assigned_user = (
        db.query(User)
        .filter(User.id == assignment.assigned_to)
        .first()
    )

    if assigned_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found",
        )

    old_assigned_to = task.assigned_to

    task.assigned_to = assigned_user.id

    # Assignment activity, audit and notification
    if old_assigned_to != task.assigned_to:
        create_task_activity(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            action="assigned",
            details=(
                f"Task assigned from user ID "
                f"{old_assigned_to} to user ID "
                f"{task.assigned_to}"
            ),
        )

        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="TASK_ASSIGNED",
            entity="task",
            entity_id=task.id,
        )

        create_notification(
            db=db,
            user_id=task.assigned_to,
            message=(
                f"You have been assigned task #{task.id}: "
                f"{task.title}."
            ),
        )

    db.commit()
    invalidate_dashboard_cache()
    db.refresh(task)

    return task
