from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    name: str
    slug: str


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUserCreate(BaseModel):
    user_id: int
    email: str
    role: str = "member"


class TenantUserResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str