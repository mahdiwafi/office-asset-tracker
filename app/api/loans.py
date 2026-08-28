# app/api/loans.py

import datetime

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Loan, User
from app.models.approval import ApprovalDecision
from app.schemas.common import Paginated
from app.schemas.loan import LoanCreate, LoanListItem, LoanRead, ReturnDecisionBody
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
	return_requested: bool | None = None,
	extend_requested: bool | None = None,
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[LoanListItem]:
	items, total = await loan_service.list_loans(
		session, borrower_id, return_requested, extend_requested, limit, offset
	)
	return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.post('/{loan_id}/return', response_model=LoanRead)
async def request_return(
	loan_id: int,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	# First half of the return flow: the borrower asks to return the
	# device. No body — the borrower does not grade their own return;
	# an approver records the returned condition in the decision.
	loan = await loan_service.request_return(session, current_user.id, loan_id)
	await session.commit()
	return loan


@router.post('/{loan_id}/return/decision', response_model=LoanRead)
async def decide_return(
	loan_id: int,
	data: ReturnDecisionBody,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	# Second half: an approver closes the loan and records the condition,
	# or cancels the pending request.
	loan = await loan_service.decide_return(
		session, current_user.id, loan_id, data.decision, data.condition_in
	)
	await session.commit()
	return loan


@router.post('/{loan_id}/extend', response_model=LoanRead)
async def request_extend(
	loan_id: int,
	new_due_date: datetime.date = fastapi.Body(embed=True),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	# First half of the extension flow: the borrower asks for a new due
	# date — the due date does not move until an approver decides (ADR
	# 0009). The same mutual exclusion applies in both directions: a
	# pending loan request blocks the extension, and a pending extension
	# blocks new loan requests on the asset.
	loan = await loan_service.request_extend(
		session, current_user.id, loan_id, new_due_date
	)
	await session.commit()
	return loan


@router.post('/{loan_id}/extend/decision', response_model=LoanRead)
async def decide_extend(
	loan_id: int,
	decision: ApprovalDecision = fastapi.Body(embed=True),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Loan:
	# Second half: an approver moves the due date to the requested date,
	# or cancels the pending request.
	loan = await loan_service.decide_extend(session, current_user.id, loan_id, decision)
	await session.commit()
	return loan
