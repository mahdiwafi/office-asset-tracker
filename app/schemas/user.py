import pydantic

from app.models.user import UserRole


class UserRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	email: str
	name: str
	role: UserRole
