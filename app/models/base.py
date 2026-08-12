import sqlalchemy
import sqlalchemy.orm as saorm

NAMING_CONVENTION: dict[str, str] = {
	'ix': 'ix_%(column_0_label)s',
	'uq': 'uq_%(table_name)s_%(column_0_name)s',
	'ck': 'ck_%(table_name)s_%(constraint_name)s',
	'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
	'pk': 'pk_%(table_name)s',
}


class Base(saorm.DeclarativeBase):
	metadata: sqlalchemy.MetaData = sqlalchemy.MetaData(
		naming_convention=NAMING_CONVENTION
	)
