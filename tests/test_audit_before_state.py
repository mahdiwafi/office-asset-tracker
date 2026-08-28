# tests/test_audit_before_state.py
# An audit entry for an *update* must capture the state before the
# mutation, not just after — otherwise the trail says "it changed" but
# cannot say what it changed from. These tests pin the update paths
# (approve, return, extend) to record before=snapshot(...).

import datetime

import sqlalchemy

from app.models import AuditEvent, LoanCondition, RequestStatus, UserRole
from app.models.approval import ApprovalDecision
from app.schemas.request import RequestCreate
from app.services.approvals import approve_request
from app.services.loans import (
	decide_extend,
	decide_return,
	request_extend,
	request_return,
)
from app.services.requests import create_request


async def _latest_event(db_session, action: str, entity_id: int) -> AuditEvent:
	event = await db_session.scalar(
		sqlalchemy.select(AuditEvent)
		.where(AuditEvent.action == action, AuditEvent.entity_id == entity_id)
		.order_by(AuditEvent.at.desc())
	)
	assert event is not None
	return event


async def test_approval_records_the_requests_before_state(
	db_session, user_factory, asset_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	requester = await user_factory(email='requester@example.com')
	asset = await asset_factory()
	request, _created = await create_request(
		db_session,
		requester.id,
		RequestCreate(asset_id=asset.id, justification='need a laptop'),
	)
	await approve_request(
		db_session, approver.id, request.id, ApprovalDecision.approved
	)
	event = await _latest_event(db_session, 'request.decide', request.id)
	assert event.before is not None
	assert event.before['status'] == RequestStatus.pending.value
	assert event.after['status'] == RequestStatus.approved.value


async def test_loan_return_records_the_before_state(
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
	event = await _latest_event(db_session, 'loan.return', loan.id)
	assert event.before is not None
	assert event.before['returned_at'] is None
	assert event.after['returned_at'] is not None


async def test_loan_extension_request_records_the_before_state(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	actor = await user_factory()
	asset = await asset_factory()
	loan = await loan_factory(asset, actor, returned=False)
	original_due = loan.due_date
	new_due = original_due + datetime.timedelta(days=7)
	await request_extend(db_session, actor.id, loan.id, new_due)
	event = await _latest_event(db_session, 'loan.extend_requested', loan.id)
	assert event.before is not None
	assert event.before['due_date'] == original_due.isoformat()
	assert event.before['extend_due_date'] is None
	assert event.after['extend_due_date'] == new_due.isoformat()


async def test_loan_extension_decision_records_the_before_state(
	db_session, user_factory, asset_factory, loan_factory
) -> None:
	approver = await user_factory(email='approver@example.com', role=UserRole.approver)
	borrower = await user_factory(email='borrower@example.com')
	asset = await asset_factory()
	loan = await loan_factory(asset, borrower, returned=False)
	original_due = loan.due_date
	new_due = original_due + datetime.timedelta(days=7)
	await request_extend(db_session, borrower.id, loan.id, new_due)
	await decide_extend(db_session, approver.id, loan.id, ApprovalDecision.approved)
	event = await _latest_event(db_session, 'loan.extend', loan.id)
	assert event.before is not None
	assert event.before['due_date'] == original_due.isoformat()
	assert event.before['extend_due_date'] == new_due.isoformat()
	assert event.after['due_date'] == new_due.isoformat()
	assert event.after['extend_due_date'] is None
