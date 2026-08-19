# app/api/audit.py

import fastapi
import sqlalchemy.orm as saorm

from app.db import get_db
from app.models import AuditEvent
from app.schemas.audit import AuditRead
from app.services import audit as audit_service

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/audit', tags=['audit'])


@router.get('', response_model=list[AuditRead])
async def list_audit(
	entity_type: str | None = None,
	session: saorm.Session = fastapi.Depends(get_db),
) -> list[AuditEvent]:
	return await audit_service.list_audit(session, entity_type)
