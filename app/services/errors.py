class DomainError(Exception):
	pass


class InventoryTagTakenError(DomainError):
	pass


class AssetNotFoundError(DomainError):
	pass


class AssetUnavailableError(DomainError):
	pass


class AssetOnLoanError(DomainError):
	pass


class AssetPoorConditionError(DomainError):
	pass


class InvalidAssetStatusTransitionError(DomainError):
	pass


class AssetHasLoanHistoryError(DomainError):
	pass


class LoanNotFoundError(DomainError):
	pass


class LoanAlreadyReturnedError(DomainError):
	pass


class ReturnAlreadyRequestedError(DomainError):
	pass


class NoReturnRequestedError(DomainError):
	pass


class LoanOverlapError(DomainError):
	pass


class LoanDurationExceededError(DomainError):
	pass


class ReturnConditionMissingError(DomainError):
	pass


class OverdueExtensionError(DomainError):
	pass


class ExtendAlreadyRequestedError(DomainError):
	pass


class NoExtendRequestedError(DomainError):
	pass


class InvalidExtensionError(DomainError):
	pass


class PendingRequestExistsError(DomainError):
	pass


class RequestNotFoundError(DomainError):
	pass


class NotAnApproverError(DomainError):
	pass


class AlreadyDecidedError(DomainError):
	pass


class TokenInvalidError(DomainError):
	pass


class TokenExpiredError(DomainError):
	pass
