from __future__ import annotations

import datetime
import enum
import typing

import sqlalchemy
import sqlalchemy.orm as saorm

if typing.TYPE_CHECKING:
	from app.models.loan import Loan

from app.models.base import Base


class AssetStatus(enum.Enum):
	available = 'available'
	loaned = 'loaned'
	damaged = 'damaged'
	maintenance = 'maintenance'
	offboarded = 'offboarded'


class AssetCondition(enum.Enum):
	new = 'new'
	good = 'good'
	fair = 'fair'
	poor = 'poor'


class Asset(Base):
	__tablename__ = 'assets'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	inventory_tag: saorm.Mapped[str] = saorm.mapped_column(
		sqlalchemy.String(64), unique=True, index=True
	)
	name: saorm.Mapped[str] = saorm.mapped_column(sqlalchemy.String(255))
	serial: saorm.Mapped[str | None] = saorm.mapped_column(sqlalchemy.String(255))
	category_id: saorm.Mapped[int] = saorm.mapped_column(
		sqlalchemy.ForeignKey('categories.id', ondelete='RESTRICT'),
		index=True,
	)
	status: saorm.Mapped[AssetStatus] = saorm.mapped_column(
		sqlalchemy.Enum(AssetStatus, native_enum=False),
		default=AssetStatus.available,
	)
	condition: saorm.Mapped[AssetCondition] = saorm.mapped_column(
		sqlalchemy.Enum(AssetCondition, native_enum=False),
		default=AssetCondition.good,
	)
	created_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()')
	)
	updated_at: saorm.Mapped[datetime.datetime] = saorm.mapped_column(
		server_default=sqlalchemy.text('now()'),
		onupdate=sqlalchemy.func.now(),
	)

	loans: saorm.Mapped[list[Loan]] = saorm.relationship(back_populates='asset')
