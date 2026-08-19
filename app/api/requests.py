# app/api/requests.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_actor_id
from app.db import get_db
from app.models import Request, RequestStatus
from app.schemas.common import Paginated
from app.schemas.request import RequestCreate, RequestRead
from app.services import requests as request_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/requests', tags=['requests'])


@router.post('', response_model=RequestRead, status_code=201)
async def create_request(
	data: RequestCreate,
	idempotency_key: str | None = fastapi.Header(default=None, alias='Idempotency-Key'),
	actor_id: int = fastapi.Depends(get_actor_id),
	session: saorm.Session = fastapi.Depends(get_db),
	response: fastapi.Response = None,
) -> Request:
	request, created = await request_service.create_request(
		session, actor_id, data, idempotency_key
	)
	if created:
		await session.commit()
		response.status_code = 201
	else:
		# Replay: the key already created this request once — return the
		# original with 200 instead of 201.
		response.status_code = 200
	return request


@router.get('', response_model=Paginated[RequestRead])
async def list_requests(
	status: RequestStatus | None = None,
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[RequestRead]:
	items, total = await request_service.list_requests(session, status, limit, offset)
	return Paginated(items=items, total=total, limit=limit, offset=offset)
