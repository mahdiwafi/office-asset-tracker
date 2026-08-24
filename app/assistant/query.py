# The query path: hybrid retrieval, citations, grounded generation.
#
# Retrieval is hybrid in a single request: BM25 full-text on `content`
# plus a vector query on `content_vector`, merged by Azure's Reciprocal
# Rank Fusion. Why hybrid rather than pure vector (the Day 6 concept
# list): staff questions are short and factual — "how long can I borrow
# a laptop?" — and BM25 matches the exact policy terms those questions
# reuse, while the vector leg catches paraphrases ("keep" ~ "borrow").
# The free tier has no semantic ranker, so hybrid + top-k is our quality
# ceiling and RRF keeps both signals honest.
#
# Generation is env-gated like telemetry: with LLM_API_KEY set, the
# answer is grounded on the retrieved excerpts; without it, the endpoint
# returns citations only. Presence of the key IS the flag. The wire
# format is OpenAI-compatible chat completions — spoken by DeepSeek (the
# default provider; the plan's fallback clause allowed any hosted LLM),
# OpenAI and Azure OpenAI alike — so the provider is a base URL and a
# model name away (ADR 0004). Generation is best-effort: a failed model
# call degrades to citations rather than a 500.
import azure.search.documents.models
import httpx

from app.assistant.embeddings import embed_texts
from app.assistant.search import _clients
from app.core.config import settings
from app.schemas.assistant import AssistantAnswer, Citation

MAX_ANSWER_TOKENS = 600
EXCERPT_CHARS = 200
# Low temperature on purpose: this is a factual-answer surface, not a
# creative one — we want the grounded text, not a flourish.
GENERATION_TEMPERATURE = 0.2
GENERATION_TIMEOUT_SECONDS = 30
# Refusal floor — the Day 7 [CP] decision, from the live score battery
# (2026-08-24): every real-word query scored >= 0.0315 while pure
# nonsense (zzzzqqqq) scored 0.0167, so 0.020 sits in a clean gap.
# Below it we refuse deterministically without spending a model call;
# above it the model itself is the referee for semantic mismatch —
# "capital of France" scores ~0.033 (RRF scores are rank-based, not
# calibrated) and only the system prompt's refusal instruction can
# catch it.
REFUSAL_SCORE_FLOOR = 0.020

SYSTEM_PROMPT = (
	'You are the ICT help-desk assistant for a small office. Answer staff '
	'questions about equipment and IT policy using ONLY the numbered '
	'excerpts the user provides. Every factual claim must be supported by '
	'at least one excerpt; cite the excerpts you used as [1], [2], and so '
	'on. If the excerpts do not answer the question, say so plainly and '
	'suggest contacting ICT. Never invent policies, dates or costs that '
	'are not in the excerpts. Keep the answer short and readable — a few '
	'sentences.'
)


def hybrid_search(question: str, *, top_k: int = 5) -> list[dict]:
	"""One request, two signals: BM25 on the text, nearest-neighbour on
	the vector. Azure merges both with RRF."""
	_, search_client = _clients()
	question_vector = embed_texts([question])[0]
	vector_query = azure.search.documents.models.VectorizedQuery(
		vector=question_vector,
		k_nearest_neighbors=top_k,
		fields='content_vector',
		kind='vector',
	)
	results = search_client.search(
		search_text=question,
		vector_queries=[vector_query],
		top=top_k,
		select=['title', 'article', 'chunk_index', 'content'],
	)
	return list(results)


def build_citations(results: list[dict]) -> list[Citation]:
	return [
		Citation(
			article_title=result['title'],
			article_slug=result['article'],
			chunk_index=result['chunk_index'],
			excerpt=result['content'][:EXCERPT_CHARS],
			score=result['@search.score'],
		)
		for result in results
	]


def build_prompt(question: str, citations: list[Citation]) -> str:
	excerpts = '\n\n'.join(
		f'[{index + 1}] ({citation.article_title}, {citation.article_slug}):\n'
		f'{citation.excerpt}'
		for index, citation in enumerate(citations)
	)
	return f'Excerpts:\n{excerpts}\n\nQuestion: {question}'


def _generate(question: str, citations: list[Citation]) -> str:
	"""OpenAI-compatible chat completions against the configured provider."""
	response = httpx.post(
		f'{settings.llm_base_url}/chat/completions',
		headers={'Authorization': f'Bearer {settings.llm_api_key}'},
		json={
			'model': settings.llm_model,
			'messages': [
				{'role': 'system', 'content': SYSTEM_PROMPT},
				{'role': 'user', 'content': build_prompt(question, citations)},
			],
			'max_tokens': MAX_ANSWER_TOKENS,
			'temperature': GENERATION_TEMPERATURE,
		},
		timeout=GENERATION_TIMEOUT_SECONDS,
	)
	response.raise_for_status()
	return response.json()['choices'][0]['message']['content']


def answer_question(question: str, *, top_k: int = 5) -> AssistantAnswer:
	"""Retrieve, cite, then (if configured) generate a grounded answer."""
	results = hybrid_search(question, top_k=top_k)
	citations = build_citations(results)
	if not citations or not settings.llm_api_key:
		# No grounding material or no model: citations-only answer. The
		# client shows the evidence either way.
		return AssistantAnswer(
			answer=None,
			generation_configured=bool(settings.llm_api_key),
			citations=citations,
		)
	if max(citation.score for citation in citations) < REFUSAL_SCORE_FLOOR:
		# Lexical garbage: nothing above the floor, so nothing to answer
		# from. Refuse without calling the model — the floor is a cheap,
		# deterministic decision, and the model stays the referee for the
		# semantic gap above it.
		return AssistantAnswer(
			answer=None, generation_configured=True, refused=True, citations=citations
		)
	# Generation is best-effort: a dead model call (wrong key, provider
	# outage) must not take the retrieved evidence down with it.
	try:
		answer = _generate(question, citations)
	except Exception:
		answer = None
	return AssistantAnswer(
		answer=answer,
		generation_configured=True,
		citations=citations,
	)
