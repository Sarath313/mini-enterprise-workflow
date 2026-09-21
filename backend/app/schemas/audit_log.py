from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    user_email: str
    action: str
    entity: str
    entity_id: int | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)