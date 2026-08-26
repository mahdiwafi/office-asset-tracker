"""poor-condition assets stay out of the pool

Revision ID: d4a0b2c3e5f8
Revises: c3f9a1e2b4d7
Create Date: 2026-08-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4a0b2c3e5f8'
down_revision: Union[str, Sequence[str], None] = 'c3f9a1e2b4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The lifecycle rule at the database layer: a poor-condition asset can
    # be damaged (awaiting repair) or in maintenance, never available or
    # loaned. The service checks catch it earlier with a clean message;
    # this constraint is the backstop that makes the invariant structural.
    op.create_check_constraint(
        'ck_assets_poor_condition_status',
        'assets',
        "condition <> 'poor' OR status IN ('damaged', 'maintenance')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_assets_poor_condition_status', 'assets', type_='check')
