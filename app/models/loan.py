import datetime
import enum

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models.asset import Asset
from app.models.base import Base
from app.models.user import User


class LoanCondition(enum.Enum):
	new = 'new'
	good = 'good'
	fair = 'fair'
	poor = 'poor'


class Loan(Base):
	__tablename__ = 'loans'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	asset_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('assets.id', ondelete='RESTRICT'),
		index=True,
	)
	borrower_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('users.id', ondelete='RESTRICT'),
		index=True,
	)
	request_id: saorm.Mapped[int | None] = saorm.mapped_column(
		sqlalchemy.ForeignKey('requests.id', ondelete='RESTRICT'),
		unique=True,
	)
	start_date: saorm.Mapped[datetime.date] = saorm.mapped_column(sqlalchemy.Date)
	due_date: saorm.Mapped[datetime.date] = saorm.mapped_column(sqlalchemy.Date)
	returned_at: saorm.Mapped[datetime.datetime | None] = saorm.mapped_column()
	return_requested_at: saorm.Mapped[datetime.datetime | None] = saorm.mapped_column()
	# A pending extension request (ADR 0009): the borrower asked for a new
	# due date and an approver has not decided yet. The loan's due_date
	# does not move while these are set — the requested date sits here.
	extend_requested_at: saorm.Mapped[datetime.datetime | None] = saorm.mapped_column()
	extend_due_date: saorm.Mapped[datetime.date | None] = saorm.mapped_column(
		sqlalchemy.Date
	)
	condition_out: saorm.Mapped[LoanCondition] = saorm.mapped_column(
		sqlalchemy.Enum(LoanCondition, native_enum=False),
	)
	condition_in: saorm.Mapped[LoanCondition | None] = saorm.mapped_column(
		sqlalchemy.Enum(LoanCondition, native_enum=False),
	)
	created_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)

	asset: saorm.Mapped[Asset] = saorm.relationship(back_populates='loans')
	borrower: saorm.Mapped[User] = saorm.relationship()
