# tests/test_transaction_boundary.py
# [CP] Day 2 — the transaction boundary on approval.
# approve_request performs four writes (Approval row, request.status,
# request.decided_at, audit entry). The service never commits — the caller
# owns the transaction. If the caller dies before committing, all four
# writes must vanish together: all-or-nothing.

import pytest
import sqlalchemy

from app.models import (
	Approval,
	Asset,
	AssetCondition,
	AssetStatus,
	AuditEvent,
	Category,
	Request,
	RequestStatus,
	User,
	UserRole,
)
from app.models.approval import ApprovalDecision
from app.services.approvals import approve_request


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
				.where(AuditEvent.action == 'request.decide')
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
