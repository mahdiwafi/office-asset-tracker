class DomainError(Exception):
	pass


class InventoryTagTakenError(DomainError):
	pass


class AssetNotFoundError(DomainError):
	pass


class AssetUnavailableError(DomainError):
	pass


class LoanOverlapError(DomainError):
	pass


class LoanDurationExceededError(DomainError):
	pass


class PendingRequestExistsError(DomainError):
	pass


class NotAnApproverError(DomainError):
	pass


class AlreadyDecidedError(DomainError):
	pass


class ReturnConditionMissingError(DomainError):
	pass


class OverdueExtensionError(DomainError):
	pass


class AssetHasLoanHistoryError(DomainError):
	pass
