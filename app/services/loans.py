import datetime

import sqlalchemy
import sqlalchemy.orm as saorm
from sqlalchemy.orm import selectinload

from app.models import Asset, AssetStatus, Loan, LoanCondition, Request
from app.models.approval import Approval, ApprovalDecision
from app.schemas.loan import LoanCreate
from app.services.audit import record, snapshot
from app.services.errors import (
	AssetNotFoundError,
	AssetUnavailableError,
	LoanAlreadyReturnedError,
	LoanDurationExceededError,
	LoanNotFoundError,
	LoanOverlapError,
	OverdueExtensionError,
	ReturnConditionMissingError,
)

MAX_LOAN_DURATION_DAYS = 30


async def create_loan(session: saorm.Session, actor_id: int, data: LoanCreate) -> Loan:
	asset: Asset | None = await session.get(Asset, data.asset_id)
	if asset is None:
		raise AssetNotFoundError(f'asset {data.asset_id} not found')
	if asset.status is not AssetStatus.available:
		raise AssetUnavailableError(
			f'asset {data.asset_id} is {asset.status.value} and cannot be loaned'
		)
	duration: datetime.timedelta = data.due_date - data.start_date
	if duration > datetime.timedelta(days=MAX_LOAN_DURATION_DAYS):
		raise LoanDurationExceededError(
			f'loan duration of {duration.days} days exceeds the maximum of '
			f'{MAX_LOAN_DURATION_DAYS} days'
		)
	overlapping: int = await session.scalar(
		sqlalchemy.select(sqlalchemy.func.count())
		.select_from(Loan)
		.where(
			Loan.asset_id == data.asset_id,
			Loan.returned_at.is_(None),
			Loan.start_date <= data.due_date,
			Loan.due_date >= data.start_date,
		)
	)
	if overlapping:
		raise LoanOverlapError(
			f'asset {data.asset_id} already has an active loan '
			f'overlapping {data.start_date} to {data.due_date}'
		)
	loan: Loan = Loan(
		asset_id=data.asset_id,
		borrower_id=data.borrower_id,
		request_id=data.request_id,
		start_date=data.start_date,
		due_date=data.due_date,
		condition_out=data.condition_out,
	)
	return await _finalize_loan(session, actor_id, loan)


async def _finalize_loan(session: saorm.Session, actor_id: int, loan: Loan) -> Loan:
	"""Shared loan write: insert, translate the exclusion constraint,
	mark the asset loaned, and audit the event."""
	session.add(loan)
	try:
		await session.flush()
	except sqlalchemy.exc.IntegrityError as error:
		# The loans_no_overlap exclusion constraint rejected a conflicting
		# insert that the application-level check above could not see (the
		# race window). Only translate exclusion violations (sqlstate 23P01);
		# FK violations keep their own meaning.
		if getattr(error.orig, 'sqlstate', None) == '23P01':
			raise LoanOverlapError(
				f'asset {loan.asset_id} already has an active loan '
				f'overlapping {loan.start_date} to {loan.due_date}'
			) from error
		raise
	asset: Asset | None = await session.get(Asset, loan.asset_id)
	if asset is not None:
		asset.status = AssetStatus.loaned
	await record(
		session,
		actor_id=actor_id,
		action='loan.create',
		entity_type='loan',
		entity_id=loan.id,
		after=snapshot(loan),
	)
	return loan


async def issue_loan_from_request(
	session: saorm.Session, actor_id: int, request: Request
) -> Loan | None:
	"""Approval-side issuance: when an approved request names an asset and
	a date range, the approval itself issues the loan. Requests without
	dates are consent-only — the loan is issued separately. There is no
	availability gate here: the request may name a period after the
	current loan ends, so the asset can be unavailable today; the
	exclusion constraint is the guarantee that matters."""
	if (
		request.asset_id is None
		or request.start_date is None
		or request.due_date is None
	):
		return None
	if request.due_date <= request.start_date:
		raise LoanDurationExceededError('due date must be after the start date')
	duration: datetime.timedelta = request.due_date - request.start_date
	if duration > datetime.timedelta(days=MAX_LOAN_DURATION_DAYS):
		raise LoanDurationExceededError(
			f'loan duration of {duration.days} days exceeds the maximum of '
			f'{MAX_LOAN_DURATION_DAYS} days'
		)
	loan: Loan = Loan(
		asset_id=request.asset_id,
		borrower_id=request.requester_id,
		request_id=request.id,
		start_date=request.start_date,
		due_date=request.due_date,
		condition_out=LoanCondition.good,
	)
	return await _finalize_loan(session, actor_id, loan)


async def return_loan(
	session: saorm.Session,
	actor_id: int,
	loan_id: int,
	condition_in: LoanCondition | None = None,
) -> Loan:
	loan: Loan | None = await session.get(Loan, loan_id)
	if loan is None:
		raise LoanNotFoundError(f'loan {loan_id} not found')
	if condition_in is None:
		raise ReturnConditionMissingError(
			f'returning loan {loan_id} requires recording the returned condition'
		)
	if loan.returned_at is not None:
		raise LoanAlreadyReturnedError(f'loan {loan_id} is already returned')
	before = snapshot(loan)
	loan.returned_at = datetime.datetime.now()
	loan.condition_in = condition_in
	await session.flush()
	asset: Asset | None = await session.get(Asset, loan.asset_id)
	if asset is not None:
		# The asset comes back to the pool; a poor-condition return keeps
		# it flagged for repair instead.
		asset.status = (
			AssetStatus.damaged
			if condition_in is LoanCondition.poor
			else AssetStatus.available
		)
	await record(
		session,
		actor_id=actor_id,
		action='loan.return',
		entity_type='loan',
		entity_id=loan.id,
		before=before,
		after=snapshot(loan),
	)
	return loan


async def extend_loan(
	session: saorm.Session, actor_id: int, loan_id: int, new_due_date: datetime.date
) -> Loan:
	loan: Loan | None = await session.get(Loan, loan_id)
	if loan is None:
		raise LoanNotFoundError(f'loan {loan_id} not found')
	if loan.returned_at is not None:
		raise LoanAlreadyReturnedError(f'loan {loan_id} is already returned')
	today: datetime.date = datetime.date.today()
	if loan.due_date < today:
		escalated: bool = False
		if loan.request_id is not None:
			approved_count: int = await session.scalar(
				sqlalchemy.select(sqlalchemy.func.count())
				.select_from(Approval)
				.where(
					Approval.request_id == loan.request_id,
					Approval.decision == ApprovalDecision.approved,
				)
			)
			escalated = approved_count > 0
		if not escalated:
			raise OverdueExtensionError(
				f'loan {loan_id} is overdue; extending it requires an approved escalation'
			)
	before = snapshot(loan)
	loan.due_date = new_due_date
	try:
		await session.flush()
	except sqlalchemy.exc.IntegrityError as error:
		# Moving an active loan's due date into another active loan's range
		# is rejected by the same exclusion constraint.
		if getattr(error.orig, 'sqlstate', None) == '23P01':
			raise LoanOverlapError(
				f'extending loan {loan_id} to {new_due_date} would overlap '
				f'another active loan'
			) from error
		raise
	await record(
		session,
		actor_id=actor_id,
		action='loan.extend',
		entity_type='loan',
		entity_id=loan.id,
		before=before,
		after=snapshot(loan),
	)
	return loan


async def list_loans(
	session: saorm.Session,
	borrower_id: int | None = None,
	limit: int = 50,
	offset: int = 0,
) -> tuple[list[dict], int]:
	query = sqlalchemy.select(Loan).order_by(Loan.start_date.desc())
	count_query = sqlalchemy.select(sqlalchemy.func.count()).select_from(Loan)
	if borrower_id is not None:
		query = query.where(Loan.borrower_id == borrower_id)
		count_query = count_query.where(Loan.borrower_id == borrower_id)
	# Eagerly loaded after the Day 3 N+1 checkpoint. Without this, a lazy
	# loan.asset / loan.borrower load is not just one extra query per row —
	# in an async session it raises MissingGreenlet (IO outside the greenlet)
	# and the list 500s on its first real row. selectinload fetches each
	# relationship in one extra query for all rows.
	loans = (
		await session.scalars(
			query.options(selectinload(Loan.asset), selectinload(Loan.borrower))
			.limit(limit)
			.offset(offset)
		)
	).all()
	total: int = await session.scalar(count_query)
	return [
		{
			'id': loan.id,
			'asset_id': loan.asset_id,
			'asset_name': loan.asset.name,
			'borrower_id': loan.borrower_id,
			'borrower_name': loan.borrower.name,
			'start_date': loan.start_date,
			'due_date': loan.due_date,
			'returned_at': loan.returned_at,
			'condition_out': loan.condition_out,
			'condition_in': loan.condition_in,
		}
		for loan in loans
	], total
