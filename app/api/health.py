import fastapi
import sqlalchemy

from app.db import engine

router: fastapi.APIRouter = fastapi.APIRouter()


@router.get('/health')
async def health(response: fastapi.Response) -> dict[str, str]:
	try:
		async with engine.connect() as connection:
			await connection.execute(sqlalchemy.text('SELECT 1'))
	except Exception:
		response.status_code = 503
		return {'status': 'degraded', 'database': 'unreachable'}
	return {'status': 'ok', 'database': 'ok'}
