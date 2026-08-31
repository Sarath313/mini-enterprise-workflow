from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_manager_or_admin,
)
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskAssign,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


# ============================================================
# CREATE TASK
# ============================================================

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
    # Validate assigned user
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
    db.commit()
    db.refresh(new_task)

    return new_task


# ============================================================
# GET ALL TASKS
# With RBAC + filtering + pagination
# ============================================================

@router.get(
    "/",
    response_model=list[TaskResponse],
)
def get_tasks(
    status: str | None = None,
    priority: str | None = None,
    assigned_to: int | None = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Prevent invalid pagination values
    if skip < 0:
        skip = 0

    if limit < 1:
        limit = 20

    # Maximum 100 tasks per request
    if limit > 100:
        limit = 100

    # --------------------------------------------------------
    # RBAC BASE QUERY
    # --------------------------------------------------------

    if current_user.role == "admin":
        query = db.query(Task)

    elif current_user.role == "manager":
        query = db.query(Task).filter(
            (Task.created_by == current_user.id)
            | (Task.assigned_to == current_user.id)
        )

    else:
        # Employee can only see assigned tasks
        query = db.query(Task).filter(
            Task.assigned_to == current_user.id
        )

    # --------------------------------------------------------
    # OPTIONAL FILTERS
    # --------------------------------------------------------

    if status is not None:
        query = query.filter(Task.status == status)

    if priority is not None:
        query = query.filter(Task.priority == priority)

    if assigned_to is not None:
        query = query.filter(Task.assigned_to == assigned_to)

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    tasks = (
        query
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return tasks


# ============================================================
# GET SINGLE TASK
# ============================================================

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

    # Admin can access every task
    if current_user.role == "admin":
        return task

    # Manager can access tasks they created or are assigned to
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

    # Employee can only access assigned tasks
    if task.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task",
        )

    return task


# ============================================================
# UPDATE TASK
# ============================================================

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

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if current_user.role == "admin":
        pass

    # --------------------------------------------------------
    # MANAGER
    # --------------------------------------------------------

    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to update this task",
            )

    # --------------------------------------------------------
    # EMPLOYEE
    # --------------------------------------------------------

    else:
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you",
            )

        # Employee must provide status
        if task_data.status is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update task status",
            )

        # Employee cannot modify other fields
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

    # --------------------------------------------------------
    # VALIDATE ASSIGNED USER
    # --------------------------------------------------------

    update_data = task_data.model_dump(
        exclude_unset=True
    )

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

    # --------------------------------------------------------
    # APPLY UPDATE
    # --------------------------------------------------------

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


# ============================================================
# DELETE TASK
# ============================================================

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

    # Admin can delete any task
    if current_user.role == "admin":
        pass

    # Manager can delete tasks they created or are assigned to
    elif current_user.role == "manager":
        if (
            task.created_by != current_user.id
            and task.assigned_to != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this task",
            )

    # Employee cannot delete tasks
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot delete tasks",
        )

    db.delete(task)
    db.commit()


# ============================================================
# ASSIGN TASK
# ============================================================

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

    # Manager can only assign tasks they created
    if current_user.role == "manager":
        if task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign tasks they created",
            )

    # Validate assigned user
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

    task.assigned_to = assigned_user.id

    db.commit()
    db.refresh(task)

    return task