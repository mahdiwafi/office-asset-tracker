import fastapi

from app.api import errors
from app.api.health import router as health_router
from app.core.config import settings

app: fastapi.FastAPI = fastapi.FastAPI(title=settings.app_name)
# Registered on the base class: FastAPI dispatches every DomainError
# subclass here, and the handler maps the concrete type to a status code.
app.add_exception_handler(errors.DomainError, errors.domain_error_handler)
app.include_router(health_router)
