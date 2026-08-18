import datetime

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Asset, AssetStatus, Loan, LoanCondition
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
				f'asset {data.asset_id} already has an active loan '
				f'overlapping {data.start_date} to {data.due_date}'
			) from error
		raise
	return loan


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
	loan.returned_at = datetime.datetime.now()
	loan.condition_in = condition_in
	await session.flush()
	await record(
		session,
		actor_id=actor_id,
		action='loan.return',
		entity_type='loan',
		entity_id=loan.id,
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
		after=snapshot(loan),
	)
	return loan
