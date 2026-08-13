import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Asset
from app.schemas.asset import AssetCreate
from app.services.errors import InventoryTagTakenError


async def create_asset(
	session: saorm.Session, actor_id: int, data: AssetCreate
) -> Asset:
	asset: Asset = Asset(
		inventory_tag=data.inventory_tag,
		name=data.name,
		serial=data.serial,
		category_id=data.category_id,
		status=data.status,
		condition=data.condition,
	)
	session.add(asset)
	try:
		await session.flush()
	except sqlalchemy.exc.IntegrityError as error:
		raise InventoryTagTakenError(
			f'asset with inventory tag {data.inventory_tag!r} already exists'
		) from error
	return asset
