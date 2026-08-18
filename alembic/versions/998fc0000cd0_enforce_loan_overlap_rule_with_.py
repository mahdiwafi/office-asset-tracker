"""enforce loan overlap rule with exclusion constraint

Revision ID: 998fc0000cd0
Revises: 2b5281268643
Create Date: 2026-08-18 14:24:12.726424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '998fc0000cd0'
down_revision: Union[str, Sequence[str], None] = '2b5281268643'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # btree_gist provides the = operator for plain (non-range) columns inside
    # a GiST index, so the exclusion constraint can combine asset_id WITH =
    # and the date range WITH && (overlap) in one constraint.
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    # daterange(start_date, due_date + 1) is half-open [start, due + 1), which
    # makes the range INCLUSIVE of the due date — matching the service rule
    # (start_date <= other.due_date AND due_date >= other.start_date).
    # The partial predicate limits enforcement to active (not yet returned)
    # loans, and because an exclusion constraint is an index, a conflicting
    # INSERT is rejected by the index itself — atomically, with no gap between
    # the application's overlap check and the insert.
    op.execute(
        'ALTER TABLE loans '
        'ADD CONSTRAINT loans_no_overlap '
        'EXCLUDE USING gist ('
        'asset_id WITH =, '
        'daterange(start_date, due_date + 1) WITH &&'
        ') '
        'WHERE (returned_at IS NULL)'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE loans DROP CONSTRAINT loans_no_overlap')
