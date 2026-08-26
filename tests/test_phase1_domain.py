# tests/test_phase1_domain.py
# Each test name is one business rule. The name IS the specification.
# All 11 rules are enforced in the service layer and tested for real.

import datetime

import pytest

from app.models import AssetStatus, LoanCondition, UserRole
from app.models.approval import ApprovalDecision
from app.schemas.asset import AssetCreate
from app.schemas.loan import LoanCreate
from app.schemas.request import RequestCreate
from app.services.approvals import approve_request
from app.services.assets import create_asset, delete_asset, update_asset_status
from app.services.errors import (
	AssetHasLoanHistoryError,
	AssetUnavailableError,
	InventoryTagTakenError,
	LoanDurationExceededError,
	LoanOverlapError,
	NotAnApproverError,
	OverdueExtensionError,
	PendingRequestExistsError,
	ReturnConditionMissingError,
)
from app.services.loans import (
	MAX_LOAN_DURATION_DAYS,
	create_loan,
	decide_return,
	extend_loan,
	request_return,
)
from app.services.requests import create_request


async def test_a_loaned_asset_cannot_be_loaned_again(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	await loan_factory(asset, actor, returned=False)
	with pytest.raises(LoanOverlapError):
		await create_loan(
			db_session,
			actor.id,
			LoanCreate(
				asset_id=asset.id,
				borrower_id=actor.id,
				start_date=datetime.date.today(),
				due_date=datetime.date.today()
				+ datetime.timedelta(days=MAX_LOAN_DURATION_DAYS),
				condition_out=LoanCondition.good,
			),
		)


async def test_an_asset_cannot_have_overlapping_active_loans(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	await loan_factory(asset, actor, returned=False)
	today = datetime.date.today()
	with pytest.raises(LoanOverlapError):
		await create_loan(
			db_session,
			actor.id,
			LoanCreate(
				asset_id=asset.id,
				borrower_id=actor.id,
				start_date=today + datetime.timedelta(days=7),
				due_date=today + datetime.timedelta(days=21),
				condition_out=LoanCondition.good,
			),
		)


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


async def test_loan_request_cannot_be_created_for_an_unavailable_asset(
	db_session, user_factory, asset_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory(status=AssetStatus.maintenance)
	with pytest.raises(AssetUnavailableError):
		await create_loan(
			db_session,
			actor.id,
			LoanCreate(
				asset_id=asset.id,
				borrower_id=actor.id,
				start_date=datetime.date.today(),
				due_date=datetime.date.today() + datetime.timedelta(days=7),
				condition_out=LoanCondition.good,
			),
		)


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


async def test_pending_approval_blocks_concurrent_request_for_same_asset(
	db_session, user_factory, asset_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	await create_request(
		db_session,
		actor.id,
		RequestCreate(asset_id=asset.id, justification='need a laptop'),
	)
	with pytest.raises(PendingRequestExistsError):
		await create_request(
			db_session,
			actor.id,
			RequestCreate(asset_id=asset.id, justification='need it too'),
		)


async def test_a_request_cannot_be_approved_by_a_non_manager(
	db_session, user_factory, asset_factory
) -> None:
	actor = await user_factory()  # staff — not an approver
	asset = await asset_factory()
	request, _created = await create_request(
		db_session,
		actor.id,
		RequestCreate(asset_id=asset.id, justification='need a laptop'),
	)
	with pytest.raises(NotAnApproverError):
		await approve_request(
			db_session, actor.id, request.id, ApprovalDecision.approved
		)


async def test_a_return_cannot_be_processed_without_recording_condition(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	actor = await user_factory()
	asset = await asset_factory()
	loan = await loan_factory(asset, actor, returned=False)
	await request_return(db_session, actor.id, loan.id)
	with pytest.raises(ReturnConditionMissingError):
		await decide_return(
			db_session, approver.id, loan.id, ApprovalDecision.approved, None
		)


async def test_an_overdue_loan_cannot_be_extended_without_escalation(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	overdue = await loan_factory(
		asset,
		actor,
		returned=False,
		due_date=datetime.date.today() - datetime.timedelta(days=1),
	)
	with pytest.raises(OverdueExtensionError):
		await extend_loan(
			db_session,
			actor.id,
			overdue.id,
			datetime.date.today() + datetime.timedelta(days=7),
		)


async def test_an_asset_state_change_cannot_commit_without_an_audit_entry(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	# The lifecycle status write is an approver action since the rule
	# change; the point of this test is the audit coupling, not the actor.
	actor = await user_factory(role=UserRole.approver)
	asset = await asset_factory()
	await update_asset_status(db_session, actor.id, asset.id, AssetStatus.maintenance)
	assert await audit_count(entity_type='asset', entity_id=asset.id) == 1
