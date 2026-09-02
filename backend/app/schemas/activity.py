from datetime import datetime

from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: int
    task_id: int | None
    user_id: int
    user_email: str
    action: str
    details: str | None
    created_at: datetime