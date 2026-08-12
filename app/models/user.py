import datetime
import enum

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models.base import Base


class UserRole(enum.Enum):
	staff = 'staff'
	approver = 'approver'
	admin = 'admin'


class User(Base):
	__tablename__ = 'users'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	entra_oid: saorm.Mapped[str | None] = saorm.mapped_column(
		sqlalchemy.String(128), unique=True
	)
	email: saorm.Mapped[str] = saorm.mapped_column(
		sqlalchemy.String(255), unique=True, index=True
	)
	name: saorm.Mapped[str] = saorm.mapped_column(sqlalchemy.String(255))
	role: saorm.Mapped[UserRole] = saorm.mapped_column(
		sqlalchemy.Enum(UserRole, native_enum=False),
		default=UserRole.staff,
	)
	created_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
