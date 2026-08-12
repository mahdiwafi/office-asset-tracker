import pydantic

from app.models.asset import AssetCondition, AssetStatus


class AssetCreate(pydantic.BaseModel):
	inventory_tag: str
	name: str
	serial: str | None = None
	category_id: int
	status: AssetStatus = AssetStatus.available
	condition: AssetCondition = AssetCondition.good


class AssetRead(pydantic.BaseModel):
	model_config = pydantic.ConfigDict(from_attributes=True)
	id: int
	inventory_tag: str
	name: str
	serial: str | None
	category_id: int
	status: AssetStatus
	condition: AssetCondition
