from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    content_type: str | None
    version: int
    uploaded_by: int
    task_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)