import pydantic

from app.models.request import RequestStatus


class RequestCreate(pydantic.BaseModel):
	asset_id: int | None = None
	category_id: int | None = None
	justification: str


class RequestRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	requester_id: int
	asset_id: int | None
	category_id: int | None
	justification: str
	status: RequestStatus
	created_at: object
	decided_at: object | None
