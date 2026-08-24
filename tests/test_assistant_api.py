# HTTP contract for POST /assistant/query: 401 without a token, 503 when
# the search service is not configured, 422 on a blank question, and 200
# with the service mocked. Retrieval and generation themselves are
# exercised in test_assistant_query.py — here we only prove the route.

from app.assistant import query as assistant_query
from app.core.config import settings
from app.schemas.assistant import AssistantAnswer, Citation


async def test_assistant_query_requires_auth(api_client):
	client, _ = api_client
	response = await client.post('/assistant/query', json={'question': 'hi'})
	assert response.status_code == 401


async def test_assistant_query_503_when_search_unconfigured(
	api_client, bearer_headers, monkeypatch
):
	monkeypatch.setattr(settings, 'ai_search_endpoint', '')
	client, _ = api_client
	response = await client.post(
		'/assistant/query', json={'question': 'hi'}, headers=bearer_headers()
	)
	assert response.status_code == 503
	assert 'not configured' in response.json()['detail']


async def test_assistant_query_rejects_blank_question(api_client, bearer_headers):
	# The route's own guard fires for whitespace-only questions — body
	# validation (min_length) passes '   ' through, so the handler must
	# strip-check. Both 422.
	client, _ = api_client
	response = await client.post(
		'/assistant/query', json={'question': '   '}, headers=bearer_headers()
	)
	assert response.status_code == 422


async def test_assistant_query_returns_answer_and_citations(
	api_client, bearer_headers, monkeypatch
):
	monkeypatch.setattr(
		settings, 'ai_search_endpoint', 'https://example.search.windows.net'
	)
	expected = AssistantAnswer(
		answer='You can keep it for 14 days.',
		generation_configured=True,
		citations=[
			Citation(
				article_title='Loan periods and renewals',
				article_slug='loan-periods',
				chunk_index=0,
				excerpt='The standard loan period is 14 days.',
				score=0.031,
			)
		],
	)

	def _fake_answer(question: str) -> AssistantAnswer:
		assert question == 'how long can I borrow a laptop?'
		return expected

	monkeypatch.setattr(assistant_query, 'answer_question', _fake_answer)
	client, _ = api_client
	response = await client.post(
		'/assistant/query',
		json={'question': 'how long can I borrow a laptop?'},
		headers=bearer_headers(),
	)
	assert response.status_code == 200
	body = response.json()
	assert body['answer'] == 'You can keep it for 14 days.'
	assert body['generation_configured'] is True
	assert body['citations'][0]['article_slug'] == 'loan-periods'
	assert body['citations'][0]['score'] == 0.031
