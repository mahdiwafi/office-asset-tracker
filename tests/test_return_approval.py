# tests/test_return_approval.py
# Returning a loan is a two-step flow, like raising a request: the
# borrower requests the return (no condition — the borrower does not
# grade their own return), and an approver closes the loan and records
# the returned condition. Each test name is one rule.
# Emails are explicit everywhere: user_factory defaults to
# staff@example.com, and two users with the same email in one test
# violates users.email uniqueness.

import pytest

from app.models import Asset, AssetCondition, AssetStatus, Loan, LoanCondition, UserRole
from app.models.approval import ApprovalDecision
from app.services.errors import (
	LoanAlreadyReturnedError,
	NoReturnRequestedError,
	NotAnApproverError,
	ReturnAlreadyRequestedError,
	ReturnConditionMissingError,
)
from app.services.loans import decide_return, request_return


async def test_borrower_requesting_a_return_marks_the_loan_pending(
	db_session, user_factory, asset_factory, loan_factory, audit_count
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	# loan_factory inserts the loan row directly, so it never flips the
	# asset — mirror the real world by marking it loaned in the setup.
	asset.status = AssetStatus.loaned
	await db_session.flush()
	await request_return(db_session, borrower.id, loan.id)
	loan = await db_session.get(Loan, loan.id)
	assert loan.return_requested_at is not None
	assert loan.returned_at is None
	# The asset stays loaned until an approver closes the loan.
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 1


async def test_an_approver_can_request_a_return_on_the_borrowers_behalf(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, approver.id, loan.id)
	loan = await db_session.get(Loan, loan.id)
	assert loan.return_requested_at is not None


async def test_a_staff_member_cannot_request_someone_elses_return(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	stranger = await user_factory(email='stranger@example.com')
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	with pytest.raises(NotAnApproverError):
		await request_return(db_session, stranger.id, loan.id)


async def test_returning_an_already_returned_loan_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=True)
	with pytest.raises(LoanAlreadyReturnedError):
		await request_return(db_session, borrower.id, loan.id)


async def test_a_second_return_request_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	with pytest.raises(ReturnAlreadyRequestedError):
		await request_return(db_session, borrower.id, loan.id)


async def test_approver_approving_a_return_closes_the_loan(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	await decide_return(
		db_session, approver.id, loan.id, ApprovalDecision.approved, LoanCondition.good
	)
	loan = await db_session.get(Loan, loan.id)
	assert loan.returned_at is not None
	assert loan.condition_in is LoanCondition.good
	assert loan.return_requested_at is None
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.available
	# The return decision is the inspection: the recorded grade becomes
	# the asset's condition, so status and condition cannot contradict.
	assert asset.condition is AssetCondition.good


async def test_approving_a_return_with_damaged_condition_flags_the_asset(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	await decide_return(
		db_session, approver.id, loan.id, ApprovalDecision.approved, LoanCondition.poor
	)
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.damaged
	# The poor grade lands on the asset itself: damaged status, poor
	# condition — never damaged while still "good".
	assert asset.condition is AssetCondition.poor


async def test_approval_requires_the_returned_condition(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	with pytest.raises(ReturnConditionMissingError):
		await decide_return(
			db_session, approver.id, loan.id, ApprovalDecision.approved, None
		)
	loan = await db_session.get(Loan, loan.id)
	assert loan.returned_at is None


async def test_only_approvers_can_decide_a_return(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	with pytest.raises(NotAnApproverError):
		await decide_return(
			db_session,
			borrower.id,
			loan.id,
			ApprovalDecision.approved,
			LoanCondition.good,
		)


async def test_declining_a_return_keeps_the_loan_active(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	asset.status = AssetStatus.loaned
	await db_session.flush()
	await request_return(db_session, borrower.id, loan.id)
	await decide_return(
		db_session, approver.id, loan.id, ApprovalDecision.declined, None
	)
	loan = await db_session.get(Loan, loan.id)
	assert loan.return_requested_at is None
	assert loan.returned_at is None
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned


async def test_deciding_a_return_that_was_never_requested_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	with pytest.raises(NoReturnRequestedError):
		await decide_return(
			db_session,
			approver.id,
			loan.id,
			ApprovalDecision.approved,
			LoanCondition.good,
		)


async def test_return_decision_leaves_an_audit_trail(
	db_session, user_factory, asset_factory, loan_factory, audit_count
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	await decide_return(
		db_session, approver.id, loan.id, ApprovalDecision.approved, LoanCondition.fair
	)
	# Exactly two events for this loan: the request and the decision.
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 2
