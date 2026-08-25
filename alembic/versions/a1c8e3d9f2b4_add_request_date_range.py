"""add date range to requests

Revision ID: a1c8e3d9f2b4
Revises: b0b98abae0cf
Create Date: 2026-08-25 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c8e3d9f2b4'
down_revision: Union[str, Sequence[str], None] = 'b0b98abae0cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('requests', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('requests', sa.Column('due_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('requests', 'due_date')
    op.drop_column('requests', 'start_date')
