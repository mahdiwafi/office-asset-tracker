import pydantic

from app.models.approval import ApprovalDecision


class ApprovalCreate(pydantic.BaseModel):
	request_id: int
	decision: ApprovalDecision
	note: str | None = None


class ApprovalRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	request_id: int
	approver_id: int
	decision: ApprovalDecision
	note: str | None
	decided_at: object
