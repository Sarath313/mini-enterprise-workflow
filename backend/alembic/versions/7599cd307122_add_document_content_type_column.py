"""add document content_type column

Revision ID: 7599cd307122
Revises: 452bbdf7f3e5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7599cd307122"
down_revision: Union[str, Sequence[str], None] = "452bbdf7f3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "documents",
        "content_type",
    )
