from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.tenant_user import TenantUser
from app.schemas.tenant import (
    TenantCreate,
    TenantUserCreate,
)


def create_tenant(
    db: Session,
    tenant_data: TenantCreate,
    created_by: str,
):
    existing = (
        db.query(Tenant)
        .filter(Tenant.slug == tenant_data.slug)
        .first()
    )

    if existing:
        return None

    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        created_by=created_by,
        is_active=True,
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def get_tenant(
    db: Session,
    tenant_id: int,
):
    return (
        db.query(Tenant)
        .filter(Tenant.id == tenant_id)
        .first()
    )


def get_tenant_users(
    db: Session,
    tenant_id: int,
):
    return (
        db.query(TenantUser)
        .filter(TenantUser.tenant_id == tenant_id)
        .order_by(TenantUser.id)
        .all()
    )


def add_tenant_user(
    db: Session,
    tenant_id: int,
    user_data: TenantUserCreate,
):
    existing = (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_data.user_id,
        )
        .first()
    )

    if existing:
        return existing

    tenant_user = TenantUser(
        tenant_id=tenant_id,
        user_id=user_data.user_id,
        email=user_data.email,
        role=user_data.role,
        is_active=True,
    )

    db.add(tenant_user)
    db.commit()
    db.refresh(tenant_user)

    return tenant_user