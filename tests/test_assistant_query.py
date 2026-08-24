# The query path: hybrid retrieval, citation building, and env-gated
# generation. The Azure SDK and the Anthropic SDK are both faked at our
# boundary — the tests prove our wiring, not the vendors'.

import anthropic

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
	monkeypatch.setattr(settings, 'anthropic_api_key', '')
	monkeypatch.setattr(
		query,
		'hybrid_search',
		lambda q, top_k: [_result(), _result('asset-care', 1, 'x' * 500)],
	)
	answer = query.answer_question(QUESTION)
	assert answer.answer is None, 'no key → no generation, but retrieval still works'
	assert answer.generation_configured is False
	assert len(answer.citations) == 2
	first = answer.citations[0]
	assert first.article_title == 'Loan periods and renewals'
	assert first.article_slug == 'loan-periods'
	assert first.chunk_index == 0
	assert first.score == 0.031
	# Excerpt is a truncated window of the chunk, not the whole chunk.
	assert answer.citations[1].excerpt == 'x' * 200


def test_answer_question_generates_when_configured(monkeypatch):
	monkeypatch.setattr(settings, 'anthropic_api_key', 'sk-test')
	monkeypatch.setattr(
		query,
		'hybrid_search',
		lambda q, top_k: [_result(content='The standard loan period is 14 days.')],
	)
	calls: list[dict] = []

	class FakeAnthropic:
		def __init__(self, **kwargs) -> None:
			self.kwargs = kwargs

		@property
		def messages(self):
			return self

		def create(self, **kwargs):
			calls.append(kwargs)
			return type(
				'Message',
				(),
				{
					'content': [
						type('TextBlock', (), {'text': 'You can keep it for 14 days.'})
					]
				},
			)

	monkeypatch.setattr(anthropic, 'Anthropic', FakeAnthropic)
	answer = query.answer_question(QUESTION)
	assert answer.answer == 'You can keep it for 14 days.'
	assert answer.generation_configured is True
	assert len(calls) == 1
	create = calls[0]
	assert create['model'] == settings.assistant_model
	assert create['max_tokens'] == query.MAX_ANSWER_TOKENS
	# Grounding: the chunk excerpt and the question must both reach the
	# model, and the system prompt must demand citations.
	prompt = create['messages'][0]['content']
	assert 'The standard loan period is 14 days.' in prompt
	assert QUESTION in prompt
	assert '[1]' in prompt
	assert 'cite' in create['system'].lower()


def test_answer_question_skips_generation_with_no_results(monkeypatch):
	monkeypatch.setattr(settings, 'anthropic_api_key', 'sk-test')
	monkeypatch.setattr(query, 'hybrid_search', lambda q, top_k: [])

	class Explosive:
		def __init__(self, **kwargs) -> None:
			raise AssertionError('generation must not run with zero citations')

	monkeypatch.setattr(anthropic, 'Anthropic', Explosive)
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
