import datetime

import sqlalchemy.orm as saorm

from app.models import Approval, Request, User
from app.models.approval import ApprovalDecision
from app.models.request import RequestStatus
from app.models.user import UserRole
from app.services.audit import record, snapshot
from app.services.errors import (
	AlreadyDecidedError,
	NotAnApproverError,
	RequestNotFoundError,
)


async def approve_request(
	session: saorm.Session,
	actor_id: int,
	request_id: int,
	decision: ApprovalDecision,
	note: str | None = None,
) -> Approval:
	approver: User | None = await session.get(User, actor_id)
	if approver is None:
		raise NotAnApproverError(f'user {actor_id} not found')
	if approver.role not in (UserRole.approver, UserRole.admin):
		raise NotAnApproverError(
			f'user {actor_id} with role {approver.role.value} cannot approve requests'
		)
	request: Request | None = await session.get(Request, request_id)
	if request is None:
		raise RequestNotFoundError(f'request {request_id} not found')
	if request.status is not RequestStatus.pending:
		raise AlreadyDecidedError(f'request {request_id} was already decided')
	approval: Approval = Approval(
		request_id=request.id, approver_id=actor_id, decision=decision, note=note
	)
	session.add(approval)
	request.status = (
		RequestStatus.approved
		if decision is ApprovalDecision.approved
		else RequestStatus.declined
	)
	request.decided_at = datetime.datetime.now()
	await session.flush()
	await record(
		session,
		actor_id=actor_id,
		action='request.decide',
		entity_type='request',
		entity_id=request.id,
		after=snapshot(request),
	)
	return approval
