# tests/test_transaction_boundary.py
# [CP] Day 2 — the transaction boundary on approval.
# approve_request performs four writes (Approval row, request.status,
# request.decided_at, audit entry). The service never commits — the caller
# owns the transaction. If the caller dies before committing, all four
# writes must vanish together: all-or-nothing.

import datetime

import pytest
import sqlalchemy

from app.models import (
	Approval,
	Asset,
	AssetCondition,
	AssetStatus,
	AuditEvent,
	Category,
	Loan,
	Request,
	RequestStatus,
	User,
	UserRole,
)
from app.models.approval import ApprovalDecision
from app.schemas.request import RequestCreate
from app.services.approvals import approve_request
from app.services.requests import create_request


async def test_approval_writes_are_all_or_nothing(session_factory) -> None:
	# Seed committed rows in their own session (same reason as the race
	# test: a session joined to an already-begun transaction cannot commit).
	async with session_factory() as seed:
		approver = User(
			email='approver@example.com', name='approver', role=UserRole.approver
		)
		seed.add(approver)
		requester = User(
			email='requester@example.com', name='requester', role=UserRole.staff
		)
		seed.add(requester)
		await seed.flush()
		category = Category(name='laptop')
		seed.add(category)
		await seed.flush()
		asset = Asset(
			inventory_tag='AST-TXB-1',
			name='MacBook Pro 14',
			category_id=category.id,
			status=AssetStatus.available,
			condition=AssetCondition.good,
		)
		seed.add(asset)
		await seed.flush()
		request = Request(
			requester_id=requester.id,
			asset_id=asset.id,
			justification='need a laptop',
		)
		seed.add(request)
		await seed.flush()
		approver_id = approver.id
		requester_id = requester.id
		asset_id = asset.id
		request_id = request.id
		await seed.commit()
	try:
		# The approval request dies mid-way: all four writes land in the
		# transaction, then the caller crashes before it gets to commit.
		with pytest.raises(RuntimeError):
			async with session_factory() as crash:
				await approve_request(
					crash, approver_id, request_id, ApprovalDecision.approved
				)
				raise RuntimeError('caller crashed before committing')
		# A fresh session proves none of the four writes survived.
		async with session_factory() as verify:
			approval_count = await verify.scalar(
				sqlalchemy.select(sqlalchemy.func.count())
				.select_from(Approval)
				.where(Approval.request_id == request_id)
			)
			request = await verify.get(Request, request_id)
			audit_count = await verify.scalar(
				sqlalchemy.select(sqlalchemy.func.count())
				.select_from(AuditEvent)
				.where(
					AuditEvent.action == 'request.decide',
					AuditEvent.entity_id == request_id,
				)
			)
			assert approval_count == 0  # write 1: Approval row — gone
			assert request.status is RequestStatus.pending  # write 2 — gone
			assert request.decided_at is None  # write 3 — gone
			assert audit_count == 0  # write 4: audit entry — gone
	finally:
		# The seed rows are committed — clean them up in FK order.
		async with session_factory() as cleanup:
			await cleanup.execute(
				sqlalchemy.delete(Request).where(Request.id == request_id)
			)
			await cleanup.execute(sqlalchemy.delete(Asset).where(Asset.id == asset_id))
			await cleanup.execute(
				sqlalchemy.delete(Category).where(Category.id == asset.category_id)
			)
			await cleanup.execute(
				sqlalchemy.delete(User).where(User.id.in_([approver_id, requester_id]))
			)
			await cleanup.commit()


async def test_approval_loan_issuance_is_atomic_with_the_decision(
	session_factory,
) -> None:
	# The same boundary, one step further: an approved request with dates
	# issues a loan inside the decision's transaction. If the caller dies
	# before committing, the loan and its audit entry vanish with the
	# decision — no orphaned loan for a decision that never happened.
	async with session_factory() as seed:
		approver = User(
			email='approver2@example.com', name='approver', role=UserRole.approver
		)
		seed.add(approver)
		requester = User(
			email='requester2@example.com', name='requester', role=UserRole.staff
		)
		seed.add(requester)
		await seed.flush()
		category = Category(name='laptop')
		seed.add(category)
		await seed.flush()
		asset = Asset(
			inventory_tag='AST-TXB-2',
			name='MacBook Pro 14',
			category_id=category.id,
			status=AssetStatus.available,
			condition=AssetCondition.good,
		)
		seed.add(asset)
		await seed.flush()
		start = datetime.date.today()
		request, _created = await create_request(
			seed,
			requester.id,
			RequestCreate(
				asset_id=asset.id,
				justification='need a laptop',
				start_date=start,
				due_date=start + datetime.timedelta(days=7),
			),
		)
		approver_id = approver.id
		requester_id = requester.id
		request_id = request.id
		asset_id = asset.id
		await seed.commit()
	try:
		with pytest.raises(RuntimeError):
			async with session_factory() as crash:
				await approve_request(
					crash, approver_id, request_id, ApprovalDecision.approved
				)
				raise RuntimeError('caller crashed before committing')
		async with session_factory() as verify:
			request = await verify.get(Request, request_id)
			loan_count = await verify.scalar(
				sqlalchemy.select(sqlalchemy.func.count())
				.select_from(Loan)
				.where(Loan.request_id == request_id)
			)
			# Scoped by entity: other tests commit their own audit events
			# (the table is never cleaned up), but a request.decide entry
			# for *this* request can only exist inside this transaction.
			audit_count = await verify.scalar(
				sqlalchemy.select(sqlalchemy.func.count())
				.select_from(AuditEvent)
				.where(
					AuditEvent.action == 'request.decide',
					AuditEvent.entity_id == request_id,
				)
			)
			assert request.status is RequestStatus.pending  # the decision — gone
			assert request.decided_at is None  # write 3 — gone
			assert loan_count == 0  # the issued loan — gone
			assert audit_count == 0  # both audit entries — gone
	finally:
		async with session_factory() as cleanup:
			await cleanup.execute(
				sqlalchemy.delete(Loan).where(Loan.request_id == request_id)
			)
			await cleanup.execute(
				sqlalchemy.delete(Request).where(Request.id == request_id)
			)
			await cleanup.execute(sqlalchemy.delete(Asset).where(Asset.id == asset_id))
			await cleanup.execute(
				sqlalchemy.delete(Category).where(Category.id == asset.category_id)
			)
			await cleanup.execute(
				sqlalchemy.delete(User).where(User.id.in_([approver_id, requester_id]))
			)
			await cleanup.commit()
