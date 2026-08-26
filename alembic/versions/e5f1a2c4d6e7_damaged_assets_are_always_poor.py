"""damaged assets are always graded poor

Revision ID: e5f1a2c4d6e7
Revises: d4a0b2c3e5f8
Create Date: 2026-08-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5f1a2c4d6e7'
down_revision: Union[str, Sequence[str], None] = 'd4a0b2c3e5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The lifecycle invariant is two-way (ADR 0008 amendment): poor
    # implies damaged or maintenance, and a damaged asset is always
    # graded poor. The return decision writes the two together; only
    # seed data ever produced damaged-but-fair, so align those rows
    # before the constraint makes the rule structural.
    op.execute(
        "UPDATE assets SET condition = 'poor' "
        "WHERE status = 'damaged' AND condition <> 'poor'"
    )
    op.create_check_constraint(
        'ck_assets_damaged_is_poor',
        'assets',
        "status <> 'damaged' OR condition = 'poor'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_assets_damaged_is_poor', 'assets', type_='check')
