import datetime
import enum

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import AuditEvent


async def record(
	session: saorm.Session,
	*,
	actor_id: int | None,
	action: str,
	entity_type: str,
	entity_id: int,
	before: dict | None = None,
	after: dict | None = None,
) -> AuditEvent:
	event: AuditEvent = AuditEvent(
		actor_id=actor_id,
		action=action,
		entity_type=entity_type,
		entity_id=entity_id,
		before=before,
		after=after,
	)
	session.add(event)
	await session.flush()
	return event


def _jsonable(value: object) -> object:
	if isinstance(value, enum.Enum):
		return value.value
	if isinstance(value, datetime.datetime):
		return value.isoformat()
	if isinstance(value, datetime.date):
		return value.isoformat()
	return value


def snapshot(entity: object) -> dict:
	values: dict = {}
	for column in entity.__table__.columns:
		values[column.name] = _jsonable(getattr(entity, column.name))
	return values


async def list_audit(
	session: saorm.Session,
	entity_type: str | None = None,
	limit: int = 50,
	offset: int = 0,
) -> tuple[list[AuditEvent], int]:
	query = sqlalchemy.select(AuditEvent).order_by(AuditEvent.at.desc())
	count_query = sqlalchemy.select(sqlalchemy.func.count()).select_from(AuditEvent)
	if entity_type is not None:
		query = query.where(AuditEvent.entity_type == entity_type)
		count_query = count_query.where(AuditEvent.entity_type == entity_type)
	total: int = await session.scalar(count_query)
	items = list(await session.scalars(query.limit(limit).offset(offset)))
	return items, total
