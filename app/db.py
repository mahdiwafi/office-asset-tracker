import collections.abc

import sqlalchemy.ext.asyncio as saio

from app.core.config import settings

engine: saio.AsyncEngine = saio.create_async_engine(
	settings.database_url, pool_pre_ping=True
)
async_session_factory: saio.async_sessionmaker[saio.AsyncSession] = (
	saio.async_sessionmaker(
		engine,
		expire_on_commit=False,
	)
)


async def get_db() -> collections.abc.AsyncIterator[saio.AsyncSession]:
	async with async_session_factory() as session:
		yield session
