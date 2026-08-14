import datetime

import sqlalchemy.orm as saorm

from app.models import Loan
from app.schemas.loan import LoanCreate
from app.services.errors import LoanDurationExceededError

MAX_LOAN_DURATION_DAYS = 30


async def create_loan(session: saorm.Session, actor_id: int, data: LoanCreate) -> Loan:
	duration: datetime.timedelta = data.due_date - data.start_date
	if duration > datetime.timedelta(days=MAX_LOAN_DURATION_DAYS):
		raise LoanDurationExceededError(
			f'loan duration of {duration.days} days exceeds the maximum of '
			f'{MAX_LOAN_DURATION_DAYS} days'
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
	await session.flush()
	return loan
