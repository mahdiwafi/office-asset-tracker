# RAG assistant over the office help docs.
#
# Pipeline: docs/help/*.md → chunk (≈400 tokens, 10% overlap — the Day 6
# [CP] decision) → embed locally (fastembed, ONNX) → index in Azure AI
# Search free tier → hybrid query (BM25 + vector, merged by RRF) →
# grounded generation (Claude API, env-gated). Decisions and trade-offs
# are recorded in docs/adr/0004-assistant-rag.md.


class AssistantNotConfigured(RuntimeError):
	"""Raised when the assistant is used without its environment config
	(AI_SEARCH_ENDPOINT / AI_SEARCH_KEY). The API router 503s instead."""
