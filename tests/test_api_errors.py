# tests/test_api_errors.py
# The HTTP status code contract: every domain failure mode maps to one 4xx.
# If the map in app/api/errors.py drifts from this list, a test goes red.

import fastapi
import pytest

from app.api import errors
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
	TokenExpiredError,
	TokenInvalidError,
)


@pytest.mark.parametrize(
	('error', 'expected_status'),
	[
		(InventoryTagTakenError('tag taken'), 409),
		(AssetNotFoundError('not found'), 404),
		(AssetUnavailableError('unavailable'), 409),
		(AssetHasLoanHistoryError('has history'), 409),
		(LoanNotFoundError('not found'), 404),
		(LoanAlreadyReturnedError('returned'), 409),
		(LoanOverlapError('overlap'), 409),
		(LoanDurationExceededError('too long'), 422),
		(ReturnConditionMissingError('missing'), 400),
		(OverdueExtensionError('overdue'), 409),
		(PendingRequestExistsError('pending'), 409),
		(RequestNotFoundError('not found'), 404),
		(NotAnApproverError('not an approver'), 403),
		(AlreadyDecidedError('decided'), 409),
		# Unknown identity: 401, unlike 403 (authenticated but not allowed).
		(TokenInvalidError('invalid'), 401),
		(TokenExpiredError('expired'), 401),
		# Unknown subclass falls back to a plain bad request.
		(DomainError('generic'), 400),
	],
)
async def test_domain_error_maps_to_http_status(
	error: DomainError, expected_status: int
) -> None:
	request: fastapi.Request = fastapi.Request({'type': 'http'})
	response = await errors.domain_error_handler(request, error)
	assert response.status_code == expected_status
