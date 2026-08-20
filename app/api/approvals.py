# app/api/approvals.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Approval, User
from app.schemas.approval import ApprovalDecisionBody, ApprovalRead
from app.services import approvals as approval_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/requests', tags=['approvals'])


@router.post('/{request_id}/decision', response_model=ApprovalRead, status_code=201)
async def decide_request(
	request_id: int,
	data: ApprovalDecisionBody,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Approval:
	approval = await approval_service.approve_request(
		session, current_user.id, request_id, data.decision, data.note
	)
	await session.commit()
	return approval
