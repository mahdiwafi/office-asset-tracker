import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Asset, AssetStatus
from app.schemas.asset import AssetCreate
from app.services.audit import record, snapshot
from app.services.errors import (
	AssetHasLoanHistoryError,
	AssetNotFoundError,
	InventoryTagTakenError,
)


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
	await record(
		session,
		actor_id=actor_id,
		action='asset.create',
		entity_type='asset',
		entity_id=asset.id,
		after=snapshot(asset),
	)
	return asset


async def update_asset_status(
	session: saorm.Session, actor_id: int, asset_id: int, new_status: AssetStatus
) -> Asset:
	asset: Asset | None = await session.get(Asset, asset_id)
	if asset is None:
		raise AssetNotFoundError(f'asset {asset_id} not found')
	before: dict = snapshot(asset)
	asset.status = new_status
	await session.flush()
	await session.refresh(asset)
	await record(
		session,
		actor_id=actor_id,
		action='asset.status_change',
		entity_type='asset',
		entity_id=asset.id,
		before=before,
		after=snapshot(asset),
	)
	return asset


async def delete_asset(session: saorm.Session, actor_id: int, asset_id: int) -> None:
	asset: Asset | None = await session.get(Asset, asset_id)
	if asset is None:
		raise AssetNotFoundError(f'asset {asset_id} not found')
	before: dict = snapshot(asset)
	await session.delete(asset)
	try:
		await session.flush()
	except sqlalchemy.exc.IntegrityError as error:
		raise AssetHasLoanHistoryError(
			f'asset {asset_id} has loan history and cannot be hard deleted'
		) from error
	await record(
		session,
		actor_id=actor_id,
		action='asset.delete',
		entity_type='asset',
		entity_id=asset_id,
		before=before,
	)


async def get_asset(session: saorm.Session, asset_id: int) -> Asset:
	asset: Asset | None = await session.get(Asset, asset_id)
	if asset is None:
		raise AssetNotFoundError(f'asset {asset_id} not found')
	return asset


async def list_assets(session: saorm.Session) -> list[Asset]:
	query = sqlalchemy.select(Asset).order_by(Asset.inventory_tag)
	return list(await session.scalars(query))
