import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Loan, Request
from app.models.request import RequestStatus
from app.schemas.request import RequestCreate
from app.services.audit import record, snapshot
from app.services.errors import PendingRequestExistsError


async def create_request(
	session: saorm.Session,
	actor_id: int,
	data: RequestCreate,
	idempotency_key: str | None = None,
) -> tuple[Request, bool]:
	# Idempotency fast path: a replay of a completed request returns the
	# original instead of creating a duplicate. The unique constraint is
	# the backstop for the check-then-act race between two simultaneous
	# first submissions (same shape as the loan overlap in Day 2).
	if idempotency_key is not None:
		existing: Request | None = await session.scalar(
			sqlalchemy.select(Request).where(Request.idempotency_key == idempotency_key)
		)
		if existing is not None:
			return existing, False
	pending_count: int = await session.scalar(
		sqlalchemy.select(sqlalchemy.func.count())
		.select_from(Request)
		.where(
			Request.asset_id == data.asset_id,
			Request.status == RequestStatus.pending,
		)
	)
	if pending_count:
		raise PendingRequestExistsError(
			f'asset {data.asset_id} already has a pending request'
		)
	pending_extend: int = await session.scalar(
		sqlalchemy.select(sqlalchemy.func.count())
		.select_from(Loan)
		.where(
			Loan.asset_id == data.asset_id,
			Loan.returned_at.is_(None),
			Loan.extend_requested_at.is_not(None),
		)
	)
	if pending_extend:
		# The other half of the two-way exclusion (ADR 0009): while the
		# current borrower's extension is pending, the asset's future is
		# not decided twice at once — the request waits for the decision.
		raise PendingRequestExistsError(
			f'asset {data.asset_id} has a pending extension request'
		)
	request: Request = Request(
		requester_id=actor_id,
		asset_id=data.asset_id,
		category_id=data.category_id,
		justification=data.justification,
		start_date=data.start_date,
		due_date=data.due_date,
		idempotency_key=idempotency_key,
	)
	session.add(request)
	try:
		await session.flush()
	except sqlalchemy.exc.IntegrityError as error:
		# The unique constraint rejected a concurrent first submission with
		# the same key. Roll back the failed insert and return the winner's
		# record. If the winner has not committed yet, re-raise — the
		# client's retry takes the fast path above.
		if (
			idempotency_key is not None
			and getattr(error.orig, 'sqlstate', None) == '23505'
		):
			await session.rollback()
			winner: Request | None = await session.scalar(
				sqlalchemy.select(Request).where(
					Request.idempotency_key == idempotency_key
				)
			)
			if winner is not None:
				return winner, False
		raise
	await record(
		session,
		actor_id=actor_id,
		action='request.create',
		entity_type='request',
		entity_id=request.id,
		after=snapshot(request),
	)
	return request, True


async def list_requests(
	session: saorm.Session,
	status: RequestStatus | None = None,
	limit: int = 50,
	offset: int = 0,
) -> tuple[list[Request], int]:
	query = sqlalchemy.select(Request).order_by(Request.created_at.desc())
	count_query = sqlalchemy.select(sqlalchemy.func.count()).select_from(Request)
	if status is not None:
		query = query.where(Request.status == status)
		count_query = count_query.where(Request.status == status)
	total: int = await session.scalar(count_query)
	items = list(await session.scalars(query.limit(limit).offset(offset)))
	return items, total
