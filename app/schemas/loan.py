import datetime

import pydantic

from app.models.approval import ApprovalDecision
from app.models.loan import LoanCondition


class ReturnDecisionBody(pydantic.BaseModel):
	# Mirrors ApprovalDecisionBody for the request flow: the approver
	# decides the return and records the returned condition. Approving
	# without a condition is refused by the service (400).
	decision: ApprovalDecision
	condition_in: LoanCondition | None = None


class LoanCreate(pydantic.BaseModel):
	asset_id: int
	borrower_id: int
	request_id: int | None = None
	start_date: datetime.date
	due_date: datetime.date
	condition_out: LoanCondition


class LoanRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	asset_id: int
	borrower_id: int
	request_id: int | None
	start_date: datetime.date
	due_date: datetime.date
	returned_at: datetime.datetime | None
	return_requested_at: datetime.datetime | None
	extend_requested_at: datetime.datetime | None
	extend_due_date: datetime.date | None
	condition_out: LoanCondition
	condition_in: LoanCondition | None


class LoanListItem(pydantic.BaseModel):
	id: int
	asset_id: int
	asset_name: str
	borrower_id: int
	borrower_name: str
	start_date: datetime.date
	due_date: datetime.date
	returned_at: datetime.datetime | None
	return_requested_at: datetime.datetime | None
	extend_requested_at: datetime.datetime | None
	extend_due_date: datetime.date | None
	condition_out: LoanCondition
	condition_in: LoanCondition | None
