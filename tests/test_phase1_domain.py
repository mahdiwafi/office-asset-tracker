# tests/test_phase1_domain.py
# Each test name is one business rule. The name IS the specification.
#
# LIVE RULES — bodies written, enforced, green. (No xfail marker.)
# SPEC STUBS — [CP] candidate-authored rule names; bodies written by the
# candidate, enforced by the service layer. xfail keeps CI green until then.
#
# Remove an xfail marker the moment a stub becomes a real test.

import datetime

import pytest

from app.models import LoanCondition
from app.schemas.asset import AssetCreate
from app.schemas.loan import LoanCreate
from app.services.assets import create_asset, delete_asset
from app.services.errors import (
	AssetHasLoanHistoryError,
	InventoryTagTakenError,
	LoanDurationExceededError,
)
from app.services.loans import MAX_LOAN_DURATION_DAYS, create_loan

# ----------------------------------------------------------------- live rules


async def test_asset_creation_fails_if_inventory_tag_is_not_unique(
	db_session, user_factory, category_factory
) -> None:
	actor = await user_factory()
	category = await category_factory()
	first_asset = AssetCreate(
		inventory_tag='INV-001', name='Macbook', category_id=category.id
	)
	await create_asset(db_session, actor.id, first_asset)
	with pytest.raises(InventoryTagTakenError):
		await create_asset(db_session, actor.id, first_asset)


async def test_an_asset_with_past_loans_cannot_be_hard_deleted(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	await loan_factory(asset, actor)
	with pytest.raises(AssetHasLoanHistoryError):
		await delete_asset(db_session, actor.id, asset.id)


async def test_loan_due_date_cannot_exceed_maximum_allowed_duration(
	db_session, user_factory, asset_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	with pytest.raises(LoanDurationExceededError):
		await create_loan(
			db_session,
			actor.id,
			LoanCreate(
				asset_id=asset.id,
				borrower_id=actor.id,
				start_date=datetime.date.today(),
				due_date=datetime.date.today()
				+ datetime.timedelta(days=MAX_LOAN_DURATION_DAYS + 1),
				condition_out=LoanCondition.good,
			),
		)


# ----------------------------------------------------------------- spec stubs


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_a_loaned_asset_cannot_be_loaned_again() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_an_asset_cannot_have_overlapping_active_loans() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_loan_request_cannot_be_created_for_an_unavailable_asset() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_pending_approval_blocks_concurrent_request_for_same_asset() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_a_request_cannot_be_approved_by_a_non_manager() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_a_return_cannot_be_processed_without_recording_condition() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_an_overdue_loan_cannot_be_extended_without_escalation() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_an_asset_state_change_cannot_commit_without_an_audit_entry() -> None:
	assert False  # spec only — fails red until implemented
