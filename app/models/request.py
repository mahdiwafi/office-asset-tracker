import datetime
import enum

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models.base import Base


class RequestStatus(enum.Enum):
	pending = 'pending'
	approved = 'approved'
	declined = 'declined'
	cancelled = 'cancelled'


class Request(Base):
	__tablename__ = 'requests'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	requester_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('users.id', ondelete='RESTRICT'),
		index=True,
	)
	asset_id: saorm.Mapped[int | None] = saorm.mapped_column(
		sqlalchemy.ForeignKey('assets.id', ondelete='RESTRICT'),
		index=True,
	)
	category_id: saorm.Mapped[int | None] = saorm.mapped_column(
		sqlalchemy.ForeignKey('categories.id', ondelete='RESTRICT'),
		index=True,
	)
	justification: saorm.Mapped[str] = saorm.mapped_column(sqlalchemy.Text)
	# Idempotency-Key header: one key may ever create one request. The
	# unique constraint is the arbiter; the service pre-check is the
	# fast path (same TOCTOU shape as the loan overlap).
	idempotency_key: saorm.Mapped[str | None] = saorm.mapped_column(
		sqlalchemy.String(64), unique=True
	)
	status: saorm.Mapped[RequestStatus] = saorm.mapped_column(
		sqlalchemy.Enum(RequestStatus, native_enum=False),
		default=RequestStatus.pending,
	)
	created_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
	decided_at: saorm.Mapped[datetime.datetime | None] = saorm.mapped_column()
