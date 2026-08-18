# tests/test_concurrency.py
# [CP] Day 2 — the race condition.
# Sequential tests pass even without a fix; this file exercises the rule
# under concurrency and pins the DB-level guarantee: the loans_no_overlap
# exclusion constraint, which rejects a conflicting INSERT inside the index
# itself — atomically, with no gap between check and insert.

import asyncio
import datetime

import pytest
import sqlalchemy

from app.models import (
	Asset,
	AssetCondition,
	AssetStatus,
	Category,
	Loan,
	LoanCondition,
	User,
	UserRole,
)
from app.schemas.loan import LoanCreate
from app.services.errors import LoanOverlapError
from app.services.loans import create_loan


async def test_parallel_loans_cannot_double_book(db_session, session_factory) -> None:
	# Seed committed rows in their own session. The db_session fixture's
	# transaction can only roll back: a Session bound to a connection that
	# already has a transaction joins it in rollback-only mode, so commit()
	# commits nothing there. The parallel sessions can only see committed
	# rows, so the seed must be committed before they run.
	async with session_factory() as seed:
		category = Category(name='laptop')
		seed.add(category)
		await seed.flush()
		category_id = category.id
		actor = User(email='staff@example.com', name='staff', role=UserRole.staff)
		seed.add(actor)
		await seed.flush()
		actor_id = actor.id
		asset = Asset(
			inventory_tag='AST-RACE-1',
			name='MacBook Pro 14',
			category_id=category_id,
			status=AssetStatus.available,
			condition=AssetCondition.good,
		)
		seed.add(asset)
		await seed.flush()
		asset_id = asset.id
		await seed.commit()
	data = LoanCreate(
		asset_id=asset_id,
		borrower_id=actor_id,
		start_date=datetime.date.today(),
		due_date=datetime.date.today() + datetime.timedelta(days=7),
		condition_out=LoanCondition.good,
	)
	try:
		async with session_factory() as first, session_factory() as second:
			# Two requests, fired at the same time. The loser blocks inside
			# its INSERT, waiting on the exclusion index, until the winner
			# commits — then the index rejects it and the service raises.
			await create_loan(first, actor_id, data)
			loser = asyncio.create_task(create_loan(second, actor_id, data))
			await asyncio.sleep(0)  # let the second request reach the database
			await first.commit()
			with pytest.raises(LoanOverlapError):
				await loser
		active_count = await db_session.scalar(
			sqlalchemy.select(sqlalchemy.func.count())
			.select_from(Loan)
			.where(
				Loan.asset_id == asset_id,
				Loan.returned_at.is_(None),
			)
		)
		assert active_count == 1
	finally:
		# The seed rows and the winner's loan are committed and survive the
		# fixture rollback — clean them up in FK order, whatever happened.
		async with session_factory() as cleanup:
			await cleanup.execute(
				sqlalchemy.delete(Loan).where(Loan.asset_id == asset_id)
			)
			await cleanup.execute(sqlalchemy.delete(Asset).where(Asset.id == asset_id))
			await cleanup.execute(
				sqlalchemy.delete(Category).where(Category.id == category_id)
			)
			await cleanup.execute(sqlalchemy.delete(User).where(User.id == actor_id))
			await cleanup.commit()
