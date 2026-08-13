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


def snapshot(entity: object) -> dict:
	return {
		column.name: getattr(entity, column.name) for column in entity.__table__.columns
	}
