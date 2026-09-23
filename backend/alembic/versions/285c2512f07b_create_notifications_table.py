"""create notifications table

Revision ID: 285c2512f07b
Revises: 7599cd307122
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "285c2512f07b"
down_revision: Union[str, Sequence[str], None] = "7599cd307122"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_notifications_id",
        "notifications",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_created_at",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_user_id",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_id",
        table_name="notifications",
    )
    op.drop_table("notifications")
