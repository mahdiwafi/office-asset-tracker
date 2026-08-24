# Local embeddings via fastembed (ONNX runtime) — deliberately no
# external embedding API.
#
# Why local: the embedding model on the original plan was Azure OpenAI,
# which is quota-blocked on free-trial subscriptions (ADR 0004). The
# local model costs nothing per call, works offline, keeps the whole
# pipeline hermetic for tests, and its 384 dimensions are far under the
# Azure AI Search free tier's 4096-dimension cap. For a twelve-chunk
# corpus, any embedding model would do — so we chose the cheapest,
# simplest one that keeps the architecture portable.
#
# The model downloads from Hugging Face on first use (a ~100 MB ONNX
# file) and is cached per process; the container image bakes the cache
# in at build time so first query is instant.

import typing

from app.core.config import settings

if typing.TYPE_CHECKING:
	from fastembed import TextEmbedding

_MODEL: 'TextEmbedding | None' = None


def _model() -> 'TextEmbedding':
	global _MODEL
	if _MODEL is None:
		# Imported lazily so the ONNX runtime never loads in environments
		# that only import this module for its signature (tests, CI).
		from fastembed import TextEmbedding

		_MODEL = TextEmbedding(
			model_name=settings.embedding_model,
			cache_dir=settings.embedding_cache_dir or None,
		)
	return _MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
	"""Embed a batch of texts into dense vectors (one per text)."""
	if not texts:
		return []
	return [vector.tolist() for vector in _model().embed(texts)]
