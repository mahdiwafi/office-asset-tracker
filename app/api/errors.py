# app/api/errors.py
# [CP] Day 3 — status code design.
# One 4xx per failure mode: not found → 404; identity/role → 403;
# payload-only → 400/422; anything the database state decides → 409.

import fastapi
import fastapi.responses

from app.services.errors import (
	AlreadyDecidedError,
	AssetHasLoanHistoryError,
	AssetNotFoundError,
	AssetUnavailableError,
	DomainError,
	InventoryTagTakenError,
	LoanAlreadyReturnedError,
	LoanDurationExceededError,
	LoanNotFoundError,
	LoanOverlapError,
	NotAnApproverError,
	OverdueExtensionError,
	PendingRequestExistsError,
	RequestNotFoundError,
	ReturnConditionMissingError,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
	InventoryTagTakenError: 409,
	AssetNotFoundError: 404,
	AssetUnavailableError: 409,
	AssetHasLoanHistoryError: 409,
	LoanNotFoundError: 404,
	LoanAlreadyReturnedError: 409,
	LoanOverlapError: 409,
	LoanDurationExceededError: 422,
	ReturnConditionMissingError: 400,
	OverdueExtensionError: 409,
	PendingRequestExistsError: 409,
	RequestNotFoundError: 404,
	NotAnApproverError: 403,
	AlreadyDecidedError: 409,
}

# Any DomainError subclass not in the map (or the base class itself).
DEFAULT_STATUS: int = 400


async def domain_error_handler(
	request: fastapi.Request, error: DomainError
) -> fastapi.responses.JSONResponse:
	status: int = DEFAULT_STATUS
	for error_type in type(error).__mro__:
		if error_type in STATUS_BY_ERROR:
			status = STATUS_BY_ERROR[error_type]
			break
	return fastapi.responses.JSONResponse(
		status_code=status, content={'detail': str(error)}
	)
