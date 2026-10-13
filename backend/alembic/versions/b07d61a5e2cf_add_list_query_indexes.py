"""add indexes for paginated list queries

Revision ID: b07d61a5e2cf
Revises: 26474fe525d5
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b07d61a5e2cf"
down_revision: Union[str, Sequence[str], None] = "26474fe525d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_tasks_assigned_recent",
        "tasks",
        [
            "assigned_to",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_tasks_created_by_recent",
        "tasks",
        [
            "created_by",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_tasks_created_recent",
        "tasks",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_documents_task_file_version",
        "documents",
        [
            "task_id",
            "file_name",
            sa.text("version DESC"),
            "id",
        ],
    )
    op.create_index(
        "ix_approvals_task_created",
        "approvals",
        ["task_id", "created_at", "id"],
    )
    op.create_index(
        "ix_approval_history_task_created",
        "approval_history",
        ["task_id", "created_at", "id"],
    )
    op.create_index(
        "ix_notifications_user_recent",
        "notifications",
        [
            "user_id",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ],
    )
    op.create_index(
        "ix_audit_logs_timestamp_id",
        "audit_logs",
        [sa.text("timestamp DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp_id", table_name="audit_logs")
    op.drop_index("ix_notifications_user_recent", table_name="notifications")
    op.drop_index(
        "ix_approval_history_task_created",
        table_name="approval_history",
    )
    op.drop_index("ix_approvals_task_created", table_name="approvals")
    op.drop_index(
        "ix_documents_task_file_version",
        table_name="documents",
    )
    op.drop_index("ix_tasks_created_recent", table_name="tasks")
    op.drop_index("ix_tasks_created_by_recent", table_name="tasks")
    op.drop_index("ix_tasks_assigned_recent", table_name="tasks")
