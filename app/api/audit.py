# app/api/audit.py

import fastapi
import sqlalchemy.orm as saorm

from app.db import get_db
from app.schemas.audit import AuditRead
from app.schemas.common import Paginated
from app.services import audit as audit_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/audit', tags=['audit'])


@router.get('', response_model=Paginated[AuditRead])
async def list_audit(
	entity_type: str | None = None,
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[AuditRead]:
	items, total = await audit_service.list_audit(session, entity_type, limit, offset)
	return Paginated(items=items, total=total, limit=limit, offset=offset)
