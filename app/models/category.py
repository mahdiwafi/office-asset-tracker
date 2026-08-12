import sqlalchemy
import sqlalchemy.orm as saorm

from app.models.base import Base


class Category(Base):
	__tablename__ = 'categories'

	id: saorm.Mapped[int] = saorm.mapped_column(primary_key=True)
	name: saorm.Mapped[str] = saorm.mapped_column(
		sqlalchemy.String(64), unique=True, index=True
	)
	description: saorm.Mapped[str | None] = saorm.mapped_column(sqlalchemy.String(255))
