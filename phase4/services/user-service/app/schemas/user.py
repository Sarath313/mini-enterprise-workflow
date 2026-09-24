from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    auth0_user_id: str
    email: str
    name: str | None = None
    picture: str | None = None
    provider: str = "unknown"


class UserUpdate(BaseModel):
    name: str | None = None
    picture: str | None = None


class UserResponse(BaseModel):
    id: int
    auth0_user_id: str
    email: str
    name: str | None
    picture: str | None
    provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)