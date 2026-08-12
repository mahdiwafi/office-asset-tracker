import pydantic


class CategoryCreate(pydantic.BaseModel):
	name: str
	description: str | None = None


class CategoryRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	name: str
	description: str | None
