"""merge audit and notification migration heads

Revision ID: d3cd5072f728
Revises: 3aea5d72aeb0, 285c2512f07b
Create Date: 2026-09-23 15:25:14.660704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3cd5072f728'
down_revision: Union[str, Sequence[str], None] = ('3aea5d72aeb0', '285c2512f07b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
