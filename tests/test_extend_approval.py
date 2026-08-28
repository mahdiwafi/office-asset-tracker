# tests/test_extend_approval.py
# Extending a loan is a two-step flow like returning one: the borrower
# requests a new due date (no condition, no consent — an approver
# decides), and an approver moves the due date or cancels the request.
# The rule is a two-way exclusion on the asset: an extension request is
# blocked while a loan request is pending on that asset, and a loan
# request is blocked while an extension request is pending — the asset's
# future is never claimed twice at once. Each test name is one rule.
# Emails are explicit everywhere: user_factory defaults to
# staff@example.com, and two users with the same email in one test
# violates users.email uniqueness.

import datetime

import pytest

from app.models import Asset, AssetStatus, Loan, UserRole
from app.models.approval import ApprovalDecision
from app.schemas.request import RequestCreate
from app.services.errors import (
	ExtendAlreadyRequestedError,
	InvalidExtensionError,
	LoanAlreadyReturnedError,
	LoanOverlapError,
	NoExtendRequestedError,
	NotAnApproverError,
	PendingRequestExistsError,
	ReturnAlreadyRequestedError,
)
from app.services.loans import decide_extend, request_extend, request_return
from app.services.requests import create_request


async def test_borrower_requesting_an_extend_marks_the_loan_pending(
	db_session, user_factory, asset_factory, loan_factory, audit_count
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	# loan_factory inserts the loan row directly, so it never flips the
	# asset — mirror the real world by marking it loaned in the setup.
	asset.status = AssetStatus.loaned
	await db_session.flush()
	original_due = loan.due_date
	new_due = original_due + datetime.timedelta(days=7)
	await request_extend(db_session, borrower.id, loan.id, new_due)
	loan = await db_session.get(Loan, loan.id)
	assert loan.extend_requested_at is not None
	assert loan.extend_due_date == new_due
	# The due date does not move until an approver decides.
	assert loan.due_date == original_due
	# The asset stays loaned — the extension changes nothing today.
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 1


async def test_an_approver_can_request_an_extend_on_the_borrowers_behalf(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_extend(
		db_session, approver.id, loan.id, loan.due_date + datetime.timedelta(days=7)
	)
	loan = await db_session.get(Loan, loan.id)
	assert loan.extend_requested_at is not None


async def test_a_staff_member_cannot_request_someone_elses_extend(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	stranger = await user_factory(email='stranger@example.com')
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	with pytest.raises(NotAnApproverError):
		await request_extend(
			db_session, stranger.id, loan.id, loan.due_date + datetime.timedelta(days=7)
		)


async def test_extending_a_returned_loan_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=True)
	with pytest.raises(LoanAlreadyReturnedError):
		await request_extend(
			db_session, borrower.id, loan.id, loan.due_date + datetime.timedelta(days=7)
		)


async def test_a_second_extend_request_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_extend(
		db_session, borrower.id, loan.id, loan.due_date + datetime.timedelta(days=7)
	)
	with pytest.raises(ExtendAlreadyRequestedError):
		await request_extend(
			db_session,
			borrower.id,
			loan.id,
			loan.due_date + datetime.timedelta(days=14),
		)


async def test_an_extend_is_rejected_while_a_return_is_pending(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_return(db_session, borrower.id, loan.id)
	# Extending a loan you have asked to return is contradictory: the
	# return and the extension claim the loan's future in opposite ways.
	with pytest.raises(ReturnAlreadyRequestedError):
		await request_extend(
			db_session, borrower.id, loan.id, loan.due_date + datetime.timedelta(days=7)
		)


async def test_an_extend_must_move_the_due_date_later(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	# Equal is not an extension, earlier is a shortening — neither moves
	# the due date later, so neither is an extend.
	with pytest.raises(InvalidExtensionError):
		await request_extend(db_session, borrower.id, loan.id, loan.due_date)
	with pytest.raises(InvalidExtensionError):
		await request_extend(
			db_session, borrower.id, loan.id, loan.due_date - datetime.timedelta(days=1)
		)


async def test_an_extend_is_rejected_while_a_loan_request_is_pending(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	# The asset's future is claimed: a loan request is pending on it, so
	# the extension waits until the approver has decided that request.
	await create_request(
		db_session,
		requester.id,
		RequestCreate(asset_id=asset.id, justification='need the asset'),
	)
	with pytest.raises(PendingRequestExistsError):
		await request_extend(
			db_session, borrower.id, loan.id, loan.due_date + datetime.timedelta(days=7)
		)


async def test_approver_approving_an_extend_moves_the_due_date(
	db_session, user_factory, asset_factory, loan_factory, audit_count
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	asset.status = AssetStatus.loaned
	await db_session.flush()
	new_due = loan.due_date + datetime.timedelta(days=7)
	await request_extend(db_session, borrower.id, loan.id, new_due)
	await decide_extend(db_session, approver.id, loan.id, ApprovalDecision.approved)
	loan = await db_session.get(Loan, loan.id)
	assert loan.due_date == new_due
	# The pending request is consumed by the decision.
	assert loan.extend_requested_at is None
	assert loan.extend_due_date is None
	assert loan.returned_at is None
	asset = await db_session.get(Asset, asset.id)
	assert asset.status is AssetStatus.loaned
	# Exactly two events for this loan: the request and the decision.
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 2


async def test_approving_an_extend_that_would_overlap_another_active_loan_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	next_borrower = await user_factory(email='next@example.com')
	asset = await asset_factory()
	# Two active loans on the same asset, back to back: the first ends
	# today+14, the second starts today+15. Extending the first into the
	# second's range is exactly what the exclusion constraint rejects.
	today = datetime.date.today()
	loan = await loan_factory(
		asset,
		borrower,
		returned=False,
		start_date=today,
		due_date=today + datetime.timedelta(days=14),
	)
	await loan_factory(
		asset,
		next_borrower,
		returned=False,
		start_date=today + datetime.timedelta(days=15),
		due_date=today + datetime.timedelta(days=28),
	)
	await request_extend(
		db_session, borrower.id, loan.id, today + datetime.timedelta(days=20)
	)
	with pytest.raises(LoanOverlapError):
		await decide_extend(db_session, approver.id, loan.id, ApprovalDecision.approved)


async def test_only_approvers_can_decide_an_extend(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	await request_extend(
		db_session, borrower.id, loan.id, loan.due_date + datetime.timedelta(days=7)
	)
	with pytest.raises(NotAnApproverError):
		await decide_extend(db_session, borrower.id, loan.id, ApprovalDecision.approved)


async def test_declining_an_extend_keeps_the_loan_unchanged(
	db_session, user_factory, asset_factory, loan_factory, audit_count
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	original_due = loan.due_date
	await request_extend(
		db_session, borrower.id, loan.id, original_due + datetime.timedelta(days=7)
	)
	await decide_extend(db_session, approver.id, loan.id, ApprovalDecision.declined)
	loan = await db_session.get(Loan, loan.id)
	assert loan.due_date == original_due
	assert loan.extend_requested_at is None
	assert loan.extend_due_date is None
	assert await audit_count(entity_type='loan', entity_id=loan.id) == 2


async def test_deciding_an_extend_that_was_never_requested_is_rejected(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	with pytest.raises(NoExtendRequestedError):
		await decide_extend(db_session, approver.id, loan.id, ApprovalDecision.approved)
