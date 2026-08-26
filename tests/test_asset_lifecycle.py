# tests/test_asset_lifecycle.py
# The asset lifecycle is a state machine, not free-form writes:
#   - poor condition implies damaged or maintenance — a poor asset can
#     never sit in the pool (available/loaned), at any layer
#   - any staff member can send an item to maintenance (not while on loan)
#   - an asset returns to the pool only out of maintenance, and the
#     repair resets the recorded condition to good
#   - offboarding is an approver's action, is blocked on loaned assets,
#     and is terminal
#   - loaning and damage are recorded by their own flows (the loan
#     creation and the return decision), never by a status write
# Each test name is one rule.
# Emails are explicit everywhere: user_factory defaults to
# staff@example.com, and two users with the same email in one test
# violates users.email uniqueness.

import pytest

from app.models import Asset, AssetCondition, AssetStatus
from app.models.user import UserRole
from app.schemas.asset import AssetCreate
from app.services.assets import create_asset, update_asset_status
from app.services.errors import (
	AssetNotFoundError,
	AssetOnLoanError,
	AssetPoorConditionError,
	InvalidAssetStatusTransitionError,
	NotAnApproverError,
)


async def test_staff_can_send_an_asset_to_maintenance(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	await update_asset_status(db_session, staff.id, asset.id, AssetStatus.maintenance)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.maintenance
	# Maintenance does not re-grade the asset — a fair mouse stays fair.
	assert asset.condition is AssetCondition.good
	assert await audit_count(entity_type='asset', entity_id=asset.id) == 1


async def test_a_loaned_asset_cannot_be_sent_to_maintenance(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	await loan_factory(asset, staff, returned=False)
	# loan_factory inserts the loan row directly, so it never flips the
	# asset — mirror the real world by marking it loaned in the setup.
	asset.status = AssetStatus.loaned
	await db_session.flush()
	with pytest.raises(AssetOnLoanError):
		await update_asset_status(
			db_session, staff.id, asset.id, AssetStatus.maintenance
		)


async def test_offboarding_requires_an_approver(
	db_session, user_factory, asset_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	with pytest.raises(NotAnApproverError):
		await update_asset_status(
			db_session, staff.id, asset.id, AssetStatus.offboarded
		)


async def test_an_approver_can_offboard_an_asset(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	asset = await asset_factory()
	await update_asset_status(db_session, approver.id, asset.id, AssetStatus.offboarded)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.offboarded
	assert await audit_count(entity_type='asset', entity_id=asset.id) == 1


async def test_an_offboarded_asset_is_terminal(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	asset = await asset_factory(status=AssetStatus.offboarded)
	with pytest.raises(InvalidAssetStatusTransitionError):
		await update_asset_status(
			db_session, approver.id, asset.id, AssetStatus.maintenance
		)


async def test_an_asset_returns_to_available_only_out_of_maintenance(
	db_session, user_factory, asset_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	# A damaged asset cannot skip the repair queue: the return-to-pool
	# path goes through maintenance.
	damaged = await asset_factory(status=AssetStatus.damaged)
	with pytest.raises(InvalidAssetStatusTransitionError):
		await update_asset_status(
			db_session, staff.id, damaged.id, AssetStatus.available
		)


async def test_repair_returns_the_asset_available_with_good_condition(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	staff = await user_factory(email='staff@example.com')
	# A poor dock in for repair: the poor grade is what put it here.
	asset = await asset_factory(
		status=AssetStatus.maintenance, condition=AssetCondition.poor
	)
	await update_asset_status(db_session, staff.id, asset.id, AssetStatus.available)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.available
	# The repair resets the grade: the pool never holds a poor asset.
	assert asset.condition is AssetCondition.good
	assert await audit_count(entity_type='asset', entity_id=asset.id) == 1


async def test_a_poor_asset_cannot_be_created_as_available(
	db_session, user_factory, category_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	category = await category_factory()
	with pytest.raises(AssetPoorConditionError):
		await create_asset(
			db_session,
			staff.id,
			AssetCreate(
				inventory_tag='IT-9999',
				name='Broken unit',
				category_id=category.id,
				status=AssetStatus.available,
				condition=AssetCondition.poor,
			),
		)


async def test_a_poor_asset_can_be_created_as_maintenance(
	db_session, user_factory, category_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	category = await category_factory()
	asset = await create_asset(
		db_session,
		staff.id,
		AssetCreate(
			inventory_tag='IT-9998',
			name='Poor dock',
			category_id=category.id,
			status=AssetStatus.maintenance,
			condition=AssetCondition.poor,
		),
	)
	assert asset.status is AssetStatus.maintenance
	assert asset.condition is AssetCondition.poor


async def test_the_status_endpoint_cannot_mark_an_asset_loaned(
	db_session, user_factory, asset_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	# Loaning is the loan flow's job (availability gate + overlap
	# exclusion), never a free status write.
	with pytest.raises(InvalidAssetStatusTransitionError):
		await update_asset_status(db_session, staff.id, asset.id, AssetStatus.loaned)


async def test_the_status_endpoint_cannot_mark_an_asset_damaged(
	db_session, user_factory, asset_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	# Damage is recorded by the return decision (the inspection), not by
	# free status writes — a damaged-but-good asset is exactly the
	# contradiction the return fix eliminated.
	with pytest.raises(InvalidAssetStatusTransitionError):
		await update_asset_status(db_session, staff.id, asset.id, AssetStatus.damaged)


async def test_a_noop_status_change_is_not_audited(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	staff = await user_factory(email='staff@example.com')
	asset = await asset_factory()
	await update_asset_status(db_session, staff.id, asset.id, AssetStatus.available)
	# No state change, so no audit event — the log records changes.
	assert await audit_count(entity_type='asset', entity_id=asset.id) == 0


async def test_status_change_on_a_missing_asset_is_rejected(
	db_session, user_factory
) -> None:
	staff = await user_factory(email='staff@example.com')
	with pytest.raises(AssetNotFoundError):
		await update_asset_status(
			db_session, staff.id, 999_999, AssetStatus.maintenance
		)


async def test_the_database_rejects_a_poor_available_asset(
	db_session, category_factory
) -> None:
	# The CHECK constraint is the backstop: even a direct ORM write cannot
	# put a poor-condition asset in the pool. (Requires the migration
	# head — the constraint ships with the feature.)
	import sqlalchemy

	category = await category_factory()
	db_session.add(
		Asset(
			inventory_tag='IT-9997',
			name='Broken unit',
			category_id=category.id,
			status=AssetStatus.available,
			condition=AssetCondition.poor,
		)
	)
	with pytest.raises(sqlalchemy.exc.IntegrityError):
		await db_session.flush()
