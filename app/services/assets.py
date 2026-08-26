import datetime

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import Asset, AssetCondition, AssetStatus, Loan, User
from app.models.user import UserRole
from app.schemas.asset import AssetCreate
from app.services.audit import record, snapshot
from app.services.errors import (
	AssetHasLoanHistoryError,
	AssetNotFoundError,
	AssetOnLoanError,
	AssetPoorConditionError,
	InvalidAssetStatusTransitionError,
	InventoryTagTakenError,
	NotAnApproverError,
)


async def create_asset(
	session: saorm.Session, actor_id: int, data: AssetCreate
) -> Asset:
	if data.condition is AssetCondition.poor and data.status not in (
		AssetStatus.damaged,
		AssetStatus.maintenance,
	):
		# The lifecycle rule: poor means the asset is out of the pool —
		# damaged awaiting repair, or already in maintenance. The catalog
		# can never show a poor asset as available or loaned.
		raise AssetPoorConditionError(
			f'a poor-condition asset starts damaged or in maintenance, '
			f'not {data.status.value}'
		)
	if data.status is AssetStatus.damaged and data.condition is not (
		AssetCondition.poor
	):
		# And the reverse: damage is always a poor grade. The return
		# decision (the inspection) writes the two together, so a damaged
		# asset cannot be created as fair or better.
		raise AssetPoorConditionError(
			f'a damaged asset must be graded poor, not {data.condition.value}'
		)
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
	"""Move an asset along the lifecycle — the status endpoint is a state
	machine, not a free-form write.

	The repair queue is the ICT team's job: sending to maintenance,
	repairing, and offboarding are approver actions (never while the
	asset is on loan); staff can loan and return, not run the queue.
	An asset comes back to the pool only out of maintenance, and the
	repair resets the recorded condition to good — a poor asset never
	sits in the pool. Offboarding is terminal. Loaning and damage are
	recorded by their own flows (loan creation, the return decision),
	never here.
	"""
	asset: Asset | None = await session.get(Asset, asset_id)
	if asset is None:
		raise AssetNotFoundError(f'asset {asset_id} not found')
	if new_status is asset.status:
		# Same status is a no-op: no state change, so no audit event.
		return asset
	if asset.status is AssetStatus.offboarded:
		raise InvalidAssetStatusTransitionError(
			f'asset {asset_id} is offboarded and cannot change status'
		)
	if new_status in (AssetStatus.loaned, AssetStatus.damaged):
		# Loaning is the loan flow's job (availability gate, overlap
		# exclusion); damage is recorded by the return decision (the
		# inspection). Neither is a status write.
		raise InvalidAssetStatusTransitionError(
			f'asset {asset_id} cannot be set to {new_status.value} via the '
			'status endpoint'
		)
	if new_status in (
		AssetStatus.maintenance,
		AssetStatus.available,
		AssetStatus.offboarded,
	):
		# The repair queue is the ICT team's job: sending to maintenance,
		# repairing, and retiring are approver actions — staff can loan
		# and return, not run the queue.
		actor: User | None = await session.get(User, actor_id)
		if actor is None or actor.role not in (UserRole.approver, UserRole.admin):
			raise NotAnApproverError(
				f'user {actor_id} cannot set asset {asset_id} to {new_status.value}'
			)
	if new_status is AssetStatus.available:
		# The repair path: the pool is reached only out of maintenance,
		# and the repair resets the grade, so status and condition stay
		# coherent (the catalog can never show a poor asset available).
		if asset.status is not AssetStatus.maintenance:
			raise InvalidAssetStatusTransitionError(
				f'asset {asset_id} is {asset.status.value}; only a '
				'maintenance asset returns to available'
			)
		asset.condition = AssetCondition.good
	if new_status is AssetStatus.offboarded and asset.status is AssetStatus.loaned:
		raise AssetOnLoanError(f'asset {asset_id} is on loan and cannot be offboarded')
	if new_status is AssetStatus.maintenance and asset.status is AssetStatus.loaned:
		raise AssetOnLoanError(
			f'asset {asset_id} is on loan and cannot be sent to maintenance'
		)
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


async def list_assets(
	session: saorm.Session, limit: int = 50, offset: int = 0
) -> tuple[list[dict], int]:
	query = sqlalchemy.select(Asset).order_by(Asset.inventory_tag)
	total: int = await session.scalar(
		sqlalchemy.select(sqlalchemy.func.count()).select_from(Asset)
	)
	items = list(await session.scalars(query.limit(limit).offset(offset)))
	# One extra query for the page, not one per row: the active loan per
	# asset (returned_at IS NULL), mapped asset_id -> due date, so a
	# loaned asset can tell the requester *until when*.
	active = list(
		await session.scalars(
			sqlalchemy.select(Loan).where(
				Loan.asset_id.in_([asset.id for asset in items]),
				Loan.returned_at.is_(None),
			)
		)
	)
	loaned_until: dict[int, datetime.date] = {
		loan.asset_id: loan.due_date for loan in active
	}
	return [
		{
			'id': asset.id,
			'inventory_tag': asset.inventory_tag,
			'name': asset.name,
			'serial': asset.serial,
			'category_id': asset.category_id,
			'status': asset.status,
			'condition': asset.condition,
			'loaned_until': loaned_until.get(asset.id),
		}
		for asset in items
	], total
