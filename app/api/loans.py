# app/api/loans.py

import datetime

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Loan, LoanCondition, User
from app.schemas.common import Paginated
from app.schemas.loan import LoanCreate, LoanListItem, LoanRead
from app.services import loans as loan_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/loans', tags=['loans'])


@router.post('', response_model=LoanRead, status_code=201)
async def create_loan(
	data: LoanCreate,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	loan = await loan_service.create_loan(session, current_user.id, data)
	await session.commit()
	return loan


@router.get('', response_model=Paginated[LoanListItem])
async def list_loans(
	borrower_id: int | None = None,
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[LoanListItem]:
	items, total = await loan_service.list_loans(session, borrower_id, limit, offset)
	return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.post('/{loan_id}/return', response_model=LoanRead)
async def return_loan(
	loan_id: int,
	condition_in: LoanCondition | None = fastapi.Body(default=None),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	loan = await loan_service.return_loan(
		session, current_user.id, loan_id, condition_in
	)
	await session.commit()
	return loan


@router.post('/{loan_id}/extend', response_model=LoanRead)
async def extend_loan(
	loan_id: int,
	new_due_date: datetime.date = fastapi.Body(),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	loan = await loan_service.extend_loan(
		session, current_user.id, loan_id, new_due_date
	)
	await session.commit()
	return loan
