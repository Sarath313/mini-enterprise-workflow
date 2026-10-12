from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


def normalize_to_naive_utc(value: datetime | None) -> datetime | None:
    """Convert timezone-aware datetimes to naive UTC for database comparisons."""
    if value is None:
        return None

    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def get_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    action: str | None = Query(default=None, min_length=1, max_length=100),
    entity: str | None = Query(default=None, min_length=1, max_length=100),
    user_id: int | None = Query(default=None, ge=1),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    start_date = normalize_to_naive_utc(start_date)
    end_date = normalize_to_naive_utc(end_date)

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be earlier than or equal to end_date",
        )

    query = (
        db.query(
            AuditLog.id,
            AuditLog.user_id,
            User.email.label("user_email"),
            AuditLog.action,
            AuditLog.entity,
            AuditLog.entity_id,
            AuditLog.timestamp,
        )
        .outerjoin(
            User,
            User.id == AuditLog.user_id,
        )
    )

    if action:
        query = query.filter(AuditLog.action == action.strip())

    if entity:
        query = query.filter(AuditLog.entity == entity.strip())

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    if start_date is not None:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date is not None:
        query = query.filter(AuditLog.timestamp <= end_date)

    audit_logs = (
        query
        .order_by(
            desc(AuditLog.timestamp),
            desc(AuditLog.id),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=log.user_email,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            timestamp=log.timestamp,
        )
        for log in audit_logs
    ]
