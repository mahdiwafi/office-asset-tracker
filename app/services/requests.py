import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Request
from app.models.request import RequestStatus
from app.schemas.request import RequestCreate
from app.services.audit import record, snapshot
from app.services.errors import PendingRequestExistsError


async def create_request(
	session: saorm.Session, actor_id: int, data: RequestCreate
) -> Request:
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
	request: Request = Request(
		requester_id=actor_id,
		asset_id=data.asset_id,
		category_id=data.category_id,
		justification=data.justification,
	)
	session.add(request)
	await session.flush()
	await record(
		session,
		actor_id=actor_id,
		action='request.create',
		entity_type='request',
		entity_id=request.id,
		after=snapshot(request),
	)
	return request


async def list_requests(
	session: saorm.Session, status: RequestStatus | None = None
) -> list[Request]:
	query = sqlalchemy.select(Request).order_by(Request.created_at.desc())
	if status is not None:
		query = query.where(Request.status == status)
	return list(await session.scalars(query))
