import collections.abc
import datetime

import pytest_asyncio
import sqlalchemy
import sqlalchemy.ext.asyncio as saio
import sqlalchemy.pool

from app.core.config import settings
from app.db import async_session_factory
from app.models import (
	Asset,
	AssetCondition,
	AssetStatus,
	AuditEvent,
	Category,
	Loan,
	LoanCondition,
	User,
	UserRole,
)

# Tests run one event loop per test; pooled connections would cross loops.
# NullPool: every test gets a fresh connection created and closed on its own loop.
TEST_ENGINE: saio.AsyncEngine = saio.create_async_engine(
	settings.database_url, poolclass=sqlalchemy.pool.NullPool
)

_tag_counter: int = 0


def _next_tag() -> str:
	global _tag_counter
	_tag_counter += 1
	return f'AST-{_tag_counter:04d}'


@pytest_asyncio.fixture
async def db_session() -> collections.abc.AsyncIterator[saio.AsyncSession]:
	async with TEST_ENGINE.connect() as connection:
		transaction = await connection.begin()
		async with async_session_factory(bind=connection) as test_session:
			yield test_session
		await transaction.rollback()


@pytest_asyncio.fixture
async def user_factory(db_session: saio.AsyncSession):
	async def _make(
		email: str = 'staff@example.com', role: UserRole = UserRole.staff
	) -> User:
		user: User = User(email=email, name=email.split('@')[0], role=role)
		db_session.add(user)
		await db_session.flush()
		return user

	return _make


@pytest_asyncio.fixture
async def category_factory(db_session: saio.AsyncSession):
	async def _make(name: str = 'laptop') -> Category:
		category: Category = Category(name=name)
		db_session.add(category)
		await db_session.flush()
		return category

	return _make


@pytest_asyncio.fixture
async def asset_factory(db_session: saio.AsyncSession, category_factory):
	async def _make(
		inventory_tag: str | None = None,
		status: AssetStatus = AssetStatus.available,
		condition: AssetCondition = AssetCondition.good,
		category: Category | None = None,
	) -> Asset:
		asset_category: Category = category or await category_factory()
		asset: Asset = Asset(
			inventory_tag=inventory_tag or _next_tag(),
			name='MacBook Pro 14',
			category_id=asset_category.id,
			status=status,
			condition=condition,
		)
		db_session.add(asset)
		await db_session.flush()
		return asset

	return _make


@pytest_asyncio.fixture
async def loan_factory(db_session: saio.AsyncSession):
	async def _make(
		asset: Asset,
		borrower: User,
		*,
		returned: bool = True,
		start_date: datetime.date | None = None,
		due_date: datetime.date | None = None,
	) -> Loan:
		today: datetime.date = datetime.date.today()
		loan: Loan = Loan(
			asset_id=asset.id,
			borrower_id=borrower.id,
			start_date=start_date or today,
			due_date=due_date or today + datetime.timedelta(days=14),
			returned_at=datetime.datetime.now() if returned else None,
			condition_out=LoanCondition.good,
		)
		db_session.add(loan)
		await db_session.flush()
		return loan

	return _make


@pytest_asyncio.fixture
async def audit_count(db_session: saio.AsyncSession):
	async def _count(
		entity_type: str | None = None, entity_id: int | None = None
	) -> int:
		query = sqlalchemy.select(sqlalchemy.func.count()).select_from(AuditEvent)
		if entity_type is not None:
			query = query.where(AuditEvent.entity_type == entity_type)
		if entity_id is not None:
			query = query.where(AuditEvent.entity_id == entity_id)
		result = await db_session.execute(query)
		return int(result.scalar_one())

	return _count
