# app/api/assets.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Asset, AssetStatus, User
from app.schemas.asset import AssetCreate, AssetRead
from app.schemas.common import Paginated
from app.services import assets as asset_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/assets', tags=['assets'])


@router.post('', response_model=AssetRead, status_code=201)
async def create_asset(
	data: AssetCreate,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Asset:
	asset = await asset_service.create_asset(session, current_user.id, data)
	await session.commit()
	return asset


@router.get('', response_model=Paginated[AssetRead])
async def list_assets(
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[AssetRead]:
	items, total = await asset_service.list_assets(session, limit, offset)
	return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.get('/{asset_id}', response_model=AssetRead)
async def get_asset(
	asset_id: int,
	session: saorm.Session = fastapi.Depends(get_db),
) -> Asset:
	return await asset_service.get_asset(session, asset_id)


@router.patch('/{asset_id}/status', response_model=AssetRead)
async def change_asset_status(
	asset_id: int,
	new_status: AssetStatus = fastapi.Body(),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Asset:
	asset = await asset_service.update_asset_status(
		session, current_user.id, asset_id, new_status
	)
	await session.commit()
	return asset


@router.delete('/{asset_id}', status_code=204)
async def delete_asset(
	asset_id: int,
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> None:
	await asset_service.delete_asset(session, current_user.id, asset_id)
	await session.commit()
