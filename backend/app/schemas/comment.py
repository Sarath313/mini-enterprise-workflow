from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CommentVisibility = Literal[
    "public",
    "internal",
]


class CommentCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    visibility: CommentVisibility = "public"


class CommentUpdate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )


class CommentResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    user_email: str
    content: str
    visibility: CommentVisibility
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )