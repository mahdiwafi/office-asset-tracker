"""loan extension requests

Revision ID: f6a2b1c4d8e9
Revises: e5f1a2c4d6e7
Create Date: 2026-08-28 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f6a2b1c4d8e9'
down_revision: Union[str, Sequence[str], None] = 'e5f1a2c4d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Extending a loan is a two-step flow like returning one (ADR 0009):
    # the borrower requests a new due date, an approver decides. These
    # two columns hold the pending request on the loan itself — the same
    # shape as return_requested_at — so the approvals queue can list
    # pending extensions next to pending returns.
    op.add_column('loans', sqlalchemy.Column('extend_requested_at', sqlalchemy.DateTime))
    op.add_column('loans', sqlalchemy.Column('extend_due_date', sqlalchemy.Date))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loans', 'extend_due_date')
    op.drop_column('loans', 'extend_requested_at')
