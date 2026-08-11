import fastapi

from app.api.health import router as health_router
from app.core.config import settings

app: fastapi.FastAPI = fastapi.FastAPI(title=settings.app_name)
app.include_router(health_router)
