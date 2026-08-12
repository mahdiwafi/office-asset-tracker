import datetime
import enum

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models.base import Base


class ApprovalDecision(enum.Enum):
	approved = 'approved'
	declined = 'declined'


class Approval(Base):
	__tablename__ = 'approvals'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	request_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('requests.id', ondelete='RESTRICT'),
		index=True,
	)
	approver_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('users.id', ondelete='RESTRICT'),
		index=True,
	)
	decision: saorm.Mapped[ApprovalDecision] = saorm.mapped_column(
		sqlalchemy.Enum(ApprovalDecision, native_enum=False),
	)
	note: saorm.Mapped[str | None] = saorm.mapped_column(sqlalchemy.String(255))
	decided_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
