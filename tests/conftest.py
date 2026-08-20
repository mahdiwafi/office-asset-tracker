import collections.abc
import contextlib
import datetime

import httpx
import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.ext.asyncio as saio
import sqlalchemy.pool

from app.core.config import settings
from app.db import async_session_factory, get_db
from app.main import app
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
from app.services import auth
from tests.token_helpers import (
	OID,
	base_payload,
	jwks_response,
	mint_token,
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
		# close(): rollback if still active, no-op if the test already committed.
		await transaction.close()


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
async def session_factory():
	# Independent session on its own connection — like a separate web
	# request. Used by the concurrency checkpoints.
	# No transaction is begun up front: a Session bound to a connection
	# that already has a transaction joins it in rollback-only mode and
	# its commit() commits nothing. Here the session starts its own
	# transaction on first use, so session.commit() really commits;
	# session.close() rolls back anything left uncommitted.
	@contextlib.asynccontextmanager
	async def _make() -> collections.abc.AsyncIterator[saio.AsyncSession]:
		connection = await TEST_ENGINE.connect()
		session = async_session_factory(bind=connection)
		try:
			yield session
		finally:
			await session.close()
			await connection.close()

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
async def api_client():
	# Runs every request through the real ASGI app (no HTTP server) on a
	# single connection with one per-test transaction. The app session is
	# bound to that connection, so it joins the outer transaction in
	# rollback-only mode (the Day 2 gotcha, now the feature): the routers'
	# session.commit() commits nothing, every request sees every other
	# request's writes, and teardown rolls the whole test back.
	# Assert through the yielded `session` — a fresh session would open a
	# new transaction and see none of the test's writes.
	connection = await TEST_ENGINE.connect()
	transaction = await connection.begin()
	session = async_session_factory(bind=connection)

	async def _override_get_db():
		yield session

	app.dependency_overrides[get_db] = _override_get_db
	transport = httpx.ASGITransport(app=app)
	async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
		yield client, session
	app.dependency_overrides.pop(get_db, None)
	await session.close()
	await transaction.close()
	await connection.close()


@pytest.fixture(scope='session', autouse=True)
def _entra_settings():
	# CI has no .env, so the tenant/client ids are empty and the service's
	# configuration guard fires before any test runs. Give the suite fake
	# values; the token helpers derive iss/aud from the same settings, so
	# both sides always agree. test_unconfigured_raises overrides them.
	if not settings.entra_tenant_id:
		settings.entra_tenant_id = '00000000-0000-0000-0000-000000000000'
	if not settings.entra_client_id:
		settings.entra_client_id = '11111111-1111-1111-1111-111111111111'


@pytest_asyncio.fixture(autouse=True)
async def jwks(monkeypatch):
	# Stub the network: serve the demo public key as the tenant's JWKS, so
	# every verify_token call is deterministic and offline. The real JWKS
	# fetch (httpx) is exercised by the live endpoint check instead.
	async def _stub_jwks() -> dict:
		return jwks_response()

	auth._jwks_cache = None
	monkeypatch.setattr(auth, '_fetch_jwks', _stub_jwks)
	yield
	auth._jwks_cache = None


@pytest.fixture
def bearer_headers():
	# Authorization header for the API tests: a token minted with the demo
	# key for the given Entra object id. The test either seeds the matching
	# user (entra_oid=oid) or exercises first-login provisioning.
	def _make(oid: str = OID, roles: list[str] | None = None) -> dict[str, str]:
		payload = base_payload(oid=oid, roles=roles or ['Staff'])
		return {'Authorization': f'Bearer {mint_token(payload)}'}

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
