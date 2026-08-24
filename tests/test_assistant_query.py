# The query path: hybrid retrieval, citation building, and env-gated
# generation. The Azure SDK and the LLM HTTP call are both faked at our
# boundary — the tests prove our wiring, not the providers'. The
# generation fake pins the exact request shape (URL, auth header, JSON
# body) so a provider mismatch can never be invisible again — that is
# the 500 that cost an hour of live debugging on Day 6.

from app.assistant import AssistantNotConfigured, query
from app.core.config import settings
from app.schemas.assistant import Citation

QUESTION = 'how long can I borrow a laptop?'


def _result(
	article: str = 'loan-periods',
	chunk_index: int = 0,
	content: str = 'The standard loan period is 14 days.',
	score: float = 0.031,
) -> dict:
	return {
		'title': 'Loan periods and renewals',
		'article': article,
		'chunk_index': chunk_index,
		'content': content,
		'@search.score': score,
	}


class FakeSearchClient:
	def __init__(self, results: list[dict]) -> None:
		self.results = results
		self.calls: list[dict] = []

	def search(self, **kwargs) -> list[dict]:
		self.calls.append(kwargs)
		return self.results


def _fake_clients(search_client) -> tuple[None, FakeSearchClient]:
	return (None, search_client)


def _fake_embed(texts: list[str]) -> list[list[float]]:
	return [[0.5] * 384 for _ in texts]


class FakeResponse:
	def __init__(self, payload: dict) -> None:
		self._payload = payload

	def raise_for_status(self) -> None:
		return None

	def json(self) -> dict:
		return self._payload


class FakePost:
	"""Stand-in for httpx.post: records every call and returns a scripted
	response or raises."""

	def __init__(
		self, payload: dict | None = None, error: Exception | None = None
	) -> None:
		self.payload = payload
		self.error = error
		self.calls: list[dict] = []

	def __call__(self, url: str, **kwargs) -> FakeResponse:
		self.calls.append({'url': url, **kwargs})
		if self.error:
			raise self.error
		return FakeResponse(self.payload)


def test_hybrid_search_sends_text_vector_and_top_k(monkeypatch):
	fake = FakeSearchClient([_result()])
	monkeypatch.setattr(query, '_clients', lambda: _fake_clients(fake))
	monkeypatch.setattr(query, 'embed_texts', _fake_embed)
	results = query.hybrid_search(QUESTION, top_k=5)
	assert results == fake.results
	assert len(fake.calls) == 1
	call = fake.calls[0]
	# Hybrid in one request: BM25 on the text plus a vector query; Azure
	# merges both with Reciprocal Rank Fusion (RRF).
	assert call['search_text'] == QUESTION
	assert call['top'] == 5
	vector_query = call['vector_queries'][0]
	assert vector_query.vector == [0.5] * 384
	assert vector_query.k_nearest_neighbors == 5
	assert vector_query.fields == 'content_vector'


def test_answer_question_returns_citations_without_api_key(monkeypatch):
	monkeypatch.setattr(settings, 'llm_api_key', '')
	monkeypatch.setattr(
		query,
		'hybrid_search',
		lambda q, top_k: [_result(), _result('asset-care', 1, 'x' * 500)],
	)
	answer = query.answer_question(QUESTION)
	assert answer.answer is None, 'no key → no generation, but retrieval still works'
	assert answer.generation_configured is False
	assert answer.refused is False, (
		'no key is not a refusal; the floor only gates generation'
	)
	assert len(answer.citations) == 2
	first = answer.citations[0]
	assert first.article_title == 'Loan periods and renewals'
	assert first.article_slug == 'loan-periods'
	assert first.chunk_index == 0
	assert first.score == 0.031
	# Excerpt is a truncated window of the chunk, not the whole chunk.
	assert answer.citations[1].excerpt == 'x' * 200


def test_answer_question_generates_when_configured(monkeypatch):
	monkeypatch.setattr(settings, 'llm_api_key', 'sk-test')
	monkeypatch.setattr(settings, 'llm_base_url', 'https://api.deepseek.com')
	monkeypatch.setattr(settings, 'llm_model', 'deepseek-chat')
	monkeypatch.setattr(
		query,
		'hybrid_search',
		lambda q, top_k: [_result(content='The standard loan period is 14 days.')],
	)
	fake = FakePost(
		payload={'choices': [{'message': {'content': 'You can keep it for 14 days.'}}]}
	)
	monkeypatch.setattr(query.httpx, 'post', fake)
	answer = query.answer_question(QUESTION)
	assert answer.answer == 'You can keep it for 14 days.'
	assert answer.generation_configured is True
	assert answer.refused is False
	assert len(fake.calls) == 1
	call = fake.calls[0]
	# The wire contract, pinned: OpenAI-compatible chat completions
	# against the configured provider.
	assert call['url'] == 'https://api.deepseek.com/chat/completions'
	assert call['headers']['Authorization'] == 'Bearer sk-test'
	body = call['json']
	assert body['model'] == 'deepseek-chat'
	assert body['max_tokens'] == query.MAX_ANSWER_TOKENS
	assert body['temperature'] == query.GENERATION_TEMPERATURE
	assert body['messages'][0]['role'] == 'system'
	assert 'cite' in body['messages'][0]['content'].lower()
	# Grounding: the chunk excerpt and the question must both reach the
	# model, numbered as [1] so the answer can cite its sources.
	prompt = body['messages'][1]['content']
	assert 'The standard loan period is 14 days.' in prompt
	assert QUESTION in prompt
	assert '[1]' in prompt


def test_below_floor_score_refuses_without_calling_the_model(monkeypatch):
	monkeypatch.setattr(settings, 'llm_api_key', 'sk-test')
	monkeypatch.setattr(
		query, 'hybrid_search', lambda q, top_k: [_result(score=0.0157)]
	)

	def explosive(*args, **kwargs):
		raise AssertionError('the model must not be called below the floor')

	monkeypatch.setattr(query.httpx, 'post', explosive)
	answer = query.answer_question(QUESTION)
	assert answer.answer is None
	assert answer.refused is True
	assert answer.generation_configured is True
	# The weak evidence still comes back — the client can show why.
	assert len(answer.citations) == 1
	assert answer.citations[0].score == 0.0157


def test_generation_failure_degrades_to_citations(monkeypatch):
	monkeypatch.setattr(settings, 'llm_api_key', 'sk-test')
	monkeypatch.setattr(
		query,
		'hybrid_search',
		lambda q, top_k: [_result(content='The standard loan period is 14 days.')],
	)
	monkeypatch.setattr(
		query.httpx, 'post', FakePost(error=RuntimeError('provider rejected the key'))
	)
	answer = query.answer_question(QUESTION)
	assert answer.answer is None, 'a dead model call must not 500 the endpoint'
	assert answer.generation_configured is True
	# The evidence survives a dead model call.
	assert len(answer.citations) == 1
	assert answer.citations[0].article_slug == 'loan-periods'


def test_answer_question_skips_generation_with_no_results(monkeypatch):
	monkeypatch.setattr(settings, 'llm_api_key', 'sk-test')
	monkeypatch.setattr(query, 'hybrid_search', lambda q, top_k: [])

	def explosive(*args, **kwargs):
		raise AssertionError('generation must not run with zero citations')

	monkeypatch.setattr(query.httpx, 'post', explosive)
	answer = query.answer_question(QUESTION)
	assert answer.answer is None
	assert answer.citations == []
	assert answer.generation_configured is True


def test_build_citations_uses_search_score_and_full_fields():
	results = [_result(score=0.031)]
	citations = query.build_citations(results)
	assert citations == [
		Citation(
			article_title='Loan periods and renewals',
			article_slug='loan-periods',
			chunk_index=0,
			excerpt='The standard loan period is 14 days.',
			score=0.031,
		)
	]


def test_build_prompt_numbers_excerpts():
	citations = query.build_citations([_result(), _result('asset-care', 1)])
	prompt = query.build_prompt(QUESTION, citations)
	assert '[1]' in prompt and 'Loan periods and renewals' in prompt
	assert '[2]' in prompt and 'asset-care' in prompt
	assert QUESTION in prompt


def test_clients_raise_clearly_when_unconfigured(monkeypatch):
	monkeypatch.setattr(settings, 'ai_search_endpoint', '')
	monkeypatch.setattr(settings, 'ai_search_key', '')
	try:
		query._clients()
	except AssistantNotConfigured as exc:
		assert 'AI_SEARCH_ENDPOINT' in str(exc)
	else:
		raise AssertionError('expected AssistantNotConfigured')
