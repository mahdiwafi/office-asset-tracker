import datetime

import pydantic


class AuditRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	actor_id: int | None
	action: str
	entity_type: str
	entity_id: int
	before: dict | None
	after: dict | None
	at: datetime.datetime
