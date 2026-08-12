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
	status: saorm.Mapped[RequestStatus] = saorm.mapped_column(
		sqlalchemy.Enum(RequestStatus, native_enum=False),
		default=RequestStatus.pending,
	)
	created_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
	decided_at: saorm.Mapped[datetime.datetime | None] = saorm.mapped_column()
