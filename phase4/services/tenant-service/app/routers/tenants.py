from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_user import TenantUser
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantUserCreate,
    TenantUserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.services.tenant_service import (
    add_tenant_user,
    create_tenant,
    get_tenant,
    get_tenant_users,
)


router = APIRouter(
    prefix="/tenants",
    tags=["Tenant Administration"],
)


def require_admin_or_owner(
    tenant: Tenant,
    current_user: dict,
):
    subject = current_user.get("sub")

    if subject != tenant.created_by:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant administrator access required",
        )


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    subject = current_user.get("sub")

    tenant = create_tenant(
        db,
        tenant_data,
        subject,
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        )

    return tenant


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
)
def get_tenant_details(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant = get_tenant(db, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    require_admin_or_owner(
        tenant,
        current_user,
    )

    return tenant


@router.get(
    "/{tenant_id}/users",
    response_model=list[TenantUserResponse],
)
def get_users(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant = get_tenant(db, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    require_admin_or_owner(
        tenant,
        current_user,
    )

    return get_tenant_users(
        db,
        tenant_id,
    )


@router.post(
    "/{tenant_id}/users",
    response_model=TenantUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user(
    tenant_id: int,
    user_data: TenantUserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant = get_tenant(db, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    require_admin_or_owner(
        tenant,
        current_user,
    )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is inactive",
        )

    return add_tenant_user(
        db,
        tenant_id,
        user_data,
    )


@router.patch(
    "/{tenant_id}/users/{user_id}/status",
    response_model=TenantUserResponse,
)
def update_user_status(
    tenant_id: int,
    user_id: int,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant = get_tenant(db, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    require_admin_or_owner(
        tenant,
        current_user,
    )

    tenant_user = (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id,
        )
        .first()
    )

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not part of this tenant",
        )

    tenant_user.is_active = status_data.is_active

    db.commit()
    db.refresh(tenant_user)

    return tenant_user


@router.patch(
    "/{tenant_id}/users/{user_id}/role",
    response_model=TenantUserResponse,
)
def update_user_role(
    tenant_id: int,
    user_id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant = get_tenant(db, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    require_admin_or_owner(
        tenant,
        current_user,
    )

    allowed_roles = {
        "admin",
        "manager",
        "member",
    }

    if role_data.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    tenant_user = (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id,
        )
        .first()
    )

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not part of this tenant",
        )

    tenant_user.role = role_data.role

    db.commit()
    db.refresh(tenant_user)

    return tenant_user