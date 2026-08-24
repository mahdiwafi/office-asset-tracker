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
# Generation is env-gated like telemetry: with ANTHROPIC_API_KEY set, the
# answer is grounded on the retrieved excerpts; without it, the endpoint
# returns citations only. Presence of the key IS the flag.
import anthropic
import azure.search.documents.models

from app.assistant.embeddings import embed_texts
from app.assistant.search import _clients
from app.core.config import settings
from app.schemas.assistant import AssistantAnswer, Citation

MAX_ANSWER_TOKENS = 600
EXCERPT_CHARS = 200

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
	client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
	message = client.messages.create(
		model=settings.assistant_model,
		max_tokens=MAX_ANSWER_TOKENS,
		system=SYSTEM_PROMPT,
		messages=[{'role': 'user', 'content': build_prompt(question, citations)}],
	)
	return ''.join(
		block.text for block in message.content if getattr(block, 'text', None)
	)


def answer_question(question: str, *, top_k: int = 5) -> AssistantAnswer:
	"""Retrieve, cite, then (if configured) generate a grounded answer."""
	results = hybrid_search(question, top_k=top_k)
	citations = build_citations(results)
	if not citations or not settings.anthropic_api_key:
		# No grounding material or no model: citations-only answer. The
		# client shows the evidence either way.
		return AssistantAnswer(
			answer=None,
			generation_configured=bool(settings.anthropic_api_key),
			citations=citations,
		)
	return AssistantAnswer(
		answer=_generate(question, citations),
		generation_configured=True,
		citations=citations,
	)
