from fastapi import APIRouter, Depends, Query
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


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def get_audit_logs(
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    audit_logs = (
        db.query(
            AuditLog.id,
            AuditLog.user_id,
            User.email.label("user_email"),
            AuditLog.action,
            AuditLog.entity,
            AuditLog.entity_id,
            AuditLog.timestamp,
        )
        .join(
            User,
            User.id == AuditLog.user_id,
        )
        .order_by(
            desc(AuditLog.timestamp),
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