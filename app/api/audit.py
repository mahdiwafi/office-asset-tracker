# app/api/audit.py

import fastapi
import sqlalchemy.orm as saorm

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import User
from app.schemas.audit import AuditRead
from app.schemas.common import Paginated
from app.services import audit as audit_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/audit', tags=['audit'])


@router.get('', response_model=Paginated[AuditRead])
async def list_audit(
	entity_type: str | None = None,
	limit: int = fastapi.Query(50, ge=1, le=200),
	offset: int = fastapi.Query(0, ge=0),
	current_user: User = fastapi.Depends(get_current_user),
	session: saorm.Session = fastapi.Depends(get_db),
) -> Paginated[AuditRead]:
	items, total = await audit_service.list_audit(session, entity_type, limit, offset)
	return Paginated(items=items, total=total, limit=limit, offset=offset)
