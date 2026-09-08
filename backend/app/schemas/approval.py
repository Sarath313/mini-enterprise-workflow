from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ApprovalLevel = Literal[
    "manager",
    "admin",
]

ApprovalStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "hold",
]

ApprovalAction = Literal[
    "submitted",
    "approved",
    "rejected",
    "hold",
]


class ApprovalCreate(BaseModel):
    level: ApprovalLevel = "manager"


class ApprovalActionRequest(BaseModel):
    action: ApprovalAction

    comment: str | None = Field(
        default=None,
        max_length=5000,
    )


class ApprovalResponse(BaseModel):
    id: int
    task_id: int
    requested_by: int
    approver_id: int
    level: ApprovalLevel
    status: ApprovalStatus
    comment: str | None
    created_at: datetime
    updated_at: datetime


class ApprovalHistoryResponse(BaseModel):
    id: int
    approval_id: int
    task_id: int
    action_by: int
    action: ApprovalAction
    comment: str | None
    created_at: datetime