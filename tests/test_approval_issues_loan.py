# tests/test_approval_issues_loan.py
# The approval flow closes the loop: a request that names an asset and a
# date range, when approved, issues the loan itself — the asset flips to
# loaned and the exclusion constraint guards the dates at approval time.
# A request without dates is consent-only (the loan is issued
# separately). Each test name is one rule.

import datetime

import pytest
import sqlalchemy

from app.models import Asset, AssetStatus, Loan, LoanCondition, UserRole
from app.models.approval import ApprovalDecision
from app.schemas.loan import LoanCreate
from app.schemas.request import RequestCreate
from app.services.approvals import approve_request
from app.services.errors import LoanDurationExceededError, LoanOverlapError
from app.services.loans import MAX_LOAN_DURATION_DAYS, create_loan, return_loan
from app.services.requests import create_request


async def test_approval_with_dates_issues_a_loan(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	start = datetime.date.today()
	due = start + datetime.timedelta(days=7)
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='need a laptop',
			start_date=start,
			due_date=due,
		),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.approved
	)
	loan = await db_session.scalar(
		sqlalchemy.select(Loan).where(Loan.request_id == request.id)
	)
	assert loan is not None
	assert loan.borrower_id == requester.id
	assert loan.asset_id == asset.id
	assert loan.start_date == start
	assert loan.due_date == due
	assert loan.condition_out is LoanCondition.good
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned


async def test_approval_overlapping_an_active_loan_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	await loan_factory(asset, requester, returned=False)
	start = datetime.date.today()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='same dates',
			start_date=start,
			due_date=start + datetime.timedelta(days=7),
		),
	)
	# The exclusion constraint fires inside the approval transaction; the
	# whole decision is rejected (the API surfaces it as 409).
	with pytest.raises(LoanOverlapError):
		await approve_request(
			db_session, approver.id, request.id, ApprovalDecision.approved
		)


async def test_approval_for_future_dates_on_a_loaned_asset_succeeds(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	today = datetime.date.today()
	await loan_factory(
		asset,
		requester,
		returned=False,
		start_date=today,
		due_date=today + datetime.timedelta(days=14),
	)
	# The asset is out on loan today, but the request is for the period
	# after the current loan ends — approval must not require the asset to
	# be available *now*.
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='after the current loan',
			start_date=today + datetime.timedelta(days=20),
			due_date=today + datetime.timedelta(days=27),
		),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.approved
	)
	loan = await db_session.scalar(
		sqlalchemy.select(Loan).where(Loan.request_id == request.id)
	)
	assert loan is not None


async def test_approval_without_dates_is_consent_only(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(asset_id=asset.id, justification='no dates yet'),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.approved
	)
	# Scoped by asset: the shared dev database may hold real loans from
	# local app testing — a global count would read them as a leak.
	loan_count = await db_session.scalar(
		sqlalchemy.select(sqlalchemy.func.count())
		.select_from(Loan)
		.where(Loan.asset_id == asset.id)
	)
	assert loan_count == 0
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.available


async def test_declined_approval_creates_no_loan(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	start = datetime.date.today()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='will be declined',
			start_date=start,
			due_date=start + datetime.timedelta(days=7),
		),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.declined
	)
	loan_count = await db_session.scalar(
		sqlalchemy.select(sqlalchemy.func.count())
		.select_from(Loan)
		.where(Loan.asset_id == asset.id)
	)
	assert loan_count == 0
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.available


async def test_approval_issued_loan_leaves_an_audit_entry(
	db_session, user_factory, asset_factory, audit_count
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	start = datetime.date.today()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='audit me',
			start_date=start,
			due_date=start + datetime.timedelta(days=7),
		),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.approved
	)
	loan = await db_session.scalar(
		sqlalchemy.select(Loan).where(Loan.request_id == request.id)
	)
	assert loan is not None
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 1


async def test_request_dates_beyond_max_duration_are_rejected(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	start = datetime.date.today()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='too long',
			start_date=start,
			due_date=start + datetime.timedelta(days=MAX_LOAN_DURATION_DAYS + 1),
		),
	)
	with pytest.raises(LoanDurationExceededError):
		await approve_request(
			db_session, approver.id, request.id, ApprovalDecision.approved
		)


async def test_inverted_request_dates_are_rejected(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	start = datetime.date.today()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(
			asset_id=asset.id,
			justification='backwards',
			start_date=start + datetime.timedelta(days=7),
			due_date=start,
		),
	)
	with pytest.raises(LoanDurationExceededError):
		await approve_request(
			db_session, approver.id, request.id, ApprovalDecision.approved
		)


async def test_create_loan_marks_the_asset_loaned(
	db_session, user_factory, asset_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
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
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned


async def test_return_loan_restores_asset_availability(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	loan = await loan_factory(asset, actor, returned=False)
	await return_loan(db_session, actor.id, loan.id, LoanCondition.good)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.available


async def test_return_loan_with_damaged_condition_keeps_asset_damaged(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	loan = await loan_factory(asset, actor, returned=False)
	await return_loan(db_session, actor.id, loan.id, LoanCondition.poor)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.damaged
