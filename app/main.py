import fastapi

from app.api import errors
from app.api.approvals import router as approvals_router
from app.api.assets import router as assets_router
from app.api.audit import router as audit_router
from app.api.health import router as health_router
from app.api.loans import router as loans_router
from app.api.requests import router as requests_router
from app.core.config import settings

app: fastapi.FastAPI = fastapi.FastAPI(title=settings.app_name)
# Registered on the base class: FastAPI dispatches every DomainError
# subclass here, and the handler maps the concrete type to a status code.
app.add_exception_handler(errors.DomainError, errors.domain_error_handler)
app.include_router(health_router)
app.include_router(assets_router)
app.include_router(loans_router)
app.include_router(requests_router)
app.include_router(approvals_router)
app.include_router(audit_router)
