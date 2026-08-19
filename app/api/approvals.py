# app/api/approvals.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_actor_id
from app.db import get_db
from app.models import Approval
from app.schemas.approval import ApprovalDecisionBody, ApprovalRead
from app.services import approvals as approval_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/requests', tags=['approvals'])


@router.post('/{request_id}/decision', response_model=ApprovalRead, status_code=201)
async def decide_request(
	request_id: int,
	data: ApprovalDecisionBody,
	actor_id: int = fastapi.Depends(get_actor_id),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Approval:
	approval = await approval_service.approve_request(
		session, actor_id, request_id, data.decision, data.note
	)
	await session.commit()
	return approval
