from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal[
    "todo",
    "in_progress",
    "review",
    "done",
]
class TaskStatusUpdate(BaseModel):
    status: TaskStatus
TaskPriority = Literal[
    "low",
    "medium",
    "high",
]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = "medium"
    due_date: datetime | None = None
    assigned_to: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assigned_to: int | None = None


class TaskAssign(BaseModel):
    assigned_to: int


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    assigned_to: int | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
class KanbanResponse(BaseModel):
    todo: list[TaskResponse]
    in_progress: list[TaskResponse]
    review: list[TaskResponse]
    done: list[TaskResponse]