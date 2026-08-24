# POST /assistant/query — grounded answers over the office help docs.
#
# Auth is the same bearer-token dependency as every other router. The
# assistant 503s until AI_SEARCH_ENDPOINT is configured (the container
# app provides it), so the route is harmless on a fresh checkout.

import asyncio

import fastapi

from app.api.dependencies import get_current_user
from app.assistant import query as query_service
from app.core.config import settings
from app.models import User
from app.schemas.assistant import AssistantAnswer, AssistantQuery

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/assistant', tags=['assistant'])


@router.post('/query', response_model=AssistantAnswer)
async def assistant_query(
	data: AssistantQuery,
	current_user: User = fastapi.Depends(get_current_user),
) -> AssistantAnswer:
	if not data.question.strip():
		raise fastapi.HTTPException(
			status_code=422, detail='question must not be blank'
		)
	if not settings.ai_search_endpoint:
		raise fastapi.HTTPException(status_code=503, detail='assistant not configured')
	# Retrieval and generation are synchronous SDK calls; run them off the
	# event loop so a slow model response cannot stall every other request.
	return await asyncio.to_thread(query_service.answer_question, data.question)
