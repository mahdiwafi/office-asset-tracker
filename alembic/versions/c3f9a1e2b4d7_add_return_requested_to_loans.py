"""add return_requested_at to loans

Revision ID: c3f9a1e2b4d7
Revises: a1c8e3d9f2b4
Create Date: 2026-08-26 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f9a1e2b4d7'
down_revision: Union[str, Sequence[str], None] = 'a1c8e3d9f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('loans', sa.Column('return_requested_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loans', 'return_requested_at')
