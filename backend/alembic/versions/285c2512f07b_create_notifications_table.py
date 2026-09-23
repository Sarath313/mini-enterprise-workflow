"""create notifications table

Revision ID: 285c2512f07b
Revises: 7599cd307122
Create Date: 2026-09-23 10:07:22.018282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '285c2512f07b'
down_revision: Union[str, Sequence[str], None] = '7599cd307122'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
