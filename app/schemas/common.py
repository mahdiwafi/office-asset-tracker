import typing

import pydantic

T = typing.TypeVar('T')


class Paginated(pydantic.BaseModel, typing.Generic[T]):  # noqa: UP046
	# Legacy PEP 484 generic form on purpose: FastAPI 0.141's response_model
	# resolution mangles the PEP 695 `class Paginated[T]` form and pydantic
	# ends up generating a schema for the raw type argument instead of the
	# response schema.
	items: list[T]
	total: int
	limit: int
	offset: int
