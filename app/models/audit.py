import datetime

import sqlalchemy
import sqlalchemy.dialects.postgresql as sapg
import sqlalchemy.orm as saorm

from app.models.base import Base


class AuditEvent(Base):
	__tablename__ = 'audit_events'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	actor_id: saorm.Mapped[int | None] = saorm.mapped_column(
		sqlalchemy.ForeignKey('users.id', ondelete='SET NULL'),
		index=True,
	)
	action: saorm.Mapped[str] = saorm.mapped_column(sqlalchemy.String(64))
	entity_type: saorm.Mapped[str] = saorm.mapped_column(sqlalchemy.String(64))
	entity_id: saorm.Mapped[int] = saorm.mapped_column(sqlalchemy.Integer)
	before: saorm.Mapped[dict | None] = saorm.mapped_column(sapg.JSONB)
	after: saorm.Mapped[dict | None] = saorm.mapped_column(sapg.JSONB)
	at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
