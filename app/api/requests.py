# app/api/requests.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_actor_id
from app.db import get_db
from app.models import Request, RequestStatus
from app.schemas.request import RequestCreate, RequestRead
from app.services import requests as request_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/requests', tags=['requests'])


@router.post('', response_model=RequestRead, status_code=201)
async def create_request(
	data: RequestCreate,
	actor_id: int = fastapi.Depends(get_actor_id),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Request:
	request = await request_service.create_request(session, actor_id, data)
	await session.commit()
	return request


@router.get('', response_model=list[RequestRead])
async def list_requests(
	status: RequestStatus | None = None,
	session: saorm.Session = fastapi.Depends(get_db),
) -> list[Request]:
	return await request_service.list_requests(session, status)
