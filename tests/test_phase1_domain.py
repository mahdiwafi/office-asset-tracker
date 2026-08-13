# tests/test_phase1_domain.py
# Each test name is one business rule. The name IS the specification.
#
# LIVE RULES — bodies written, enforced, green. (No xfail marker.)
# SPEC STUBS — [CP] candidate-authored rule names; bodies written by the
# candidate, enforced by the service layer. xfail keeps CI green until then.
#
# Remove an xfail marker the moment a stub becomes a real test.

import pytest

from app.schemas.asset import AssetCreate
from app.services.assets import create_asset
from app.services.errors import InventoryTagTakenError

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


# ----------------------------------------------------------------- spec stubs


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_a_loaned_asset_cannot_be_loaned_again() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_an_asset_cannot_have_overlapping_active_loans() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_an_asset_with_past_loans_cannot_be_hard_deleted() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_loan_request_cannot_be_created_for_an_unavailable_asset() -> None:
	assert False  # spec only — fails red until implemented


@pytest.mark.xfail(reason='[CP] spec only — enforced in Day 2 service layer')
async def test_loan_due_date_cannot_exceed_maximum_allowed_duration() -> None:
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
