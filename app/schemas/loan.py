import datetime

import pydantic

from app.models.loan import LoanCondition


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
	condition_out: LoanCondition
	condition_in: LoanCondition | None
