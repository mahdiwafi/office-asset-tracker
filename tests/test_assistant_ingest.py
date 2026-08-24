# The upload → chunk → embed → index pipeline, with every external SDK
# call swapped for a fake: CI has no Azure, and the tests must prove the
# pipeline's *contract* (index schema, doc ids, vector dims, markdown
# stripping) — not Azure's behavior.

import pathlib

import azure.core.exceptions

from app.assistant import ingest

EMBED_DIMS = 384  # BAAI/bge-small-en-v1.5 — must match the index schema


class FakeIndexClient:
	"""Records create_index calls; get_index only succeeds for names the
	test has pre-seeded, so the idempotency branch is exercised."""

	def __init__(self, existing: set[str] | None = None) -> None:
		self.existing: set[str] = set(existing or set())
		self.created: list = []

	def get_index(self, name: str):
		if name not in self.existing:
			raise azure.core.exceptions.ResourceNotFoundError(name)
		return object()

	def create_index(self, index):
		self.created.append(index)
		self.existing.add(index.name)
		return index


class FakeSearchClient:
	def __init__(self) -> None:
		self.uploads: list[list[dict]] = []

	def upload_documents(self, documents: list[dict]) -> list:
		self.uploads.append(documents)
		return []


def _fake_embed(texts: list[str]) -> list[list[float]]:
	# Deterministic vector per text; length must match EMBED_DIMS.
	return [[0.1] * EMBED_DIMS for _ in texts]


def _write_article(dir: pathlib.Path, slug: str, title: str, body: str) -> None:
	dir.joinpath(f'{slug}.md').write_text(f'# {title}\n\n{body}')


def _run(tmp_path: pathlib.Path, existing: set[str] | None = None) -> tuple:
	index_client = FakeIndexClient(existing)
	search_client = FakeSearchClient()
	ingest.run_ingest(
		help_dir=tmp_path,
		embedder=_fake_embed,
		index_client=index_client,
		search_client=search_client,
	)
	return index_client, search_client


def test_ingest_creates_index_with_vector_schema(tmp_path):
	_write_article(
		tmp_path, 'loan-periods', 'Loan periods', 'Fourteen days is the standard loan.'
	)
	index_client, _ = _run(tmp_path)
	assert len(index_client.created) == 1
	index = index_client.created[0]
	assert index.name == ingest.INDEX_NAME
	fields = {field.name: field for field in index.fields}
	# Key + metadata + content + vector: the vector field is where the
	# schema earns its keep — dims must match the embedding model and the
	# profile must reference the HNSW algorithm.
	assert fields['id'].key is True
	assert fields['content_vector'].vector_search_dimensions == EMBED_DIMS
	assert fields['content_vector'].vector_search_profile_name == 'help-vector-profile'
	profile_names = {p.name for p in index.vector_search.profiles}
	assert 'help-vector-profile' in profile_names


def test_ingest_skips_create_when_index_already_exists(tmp_path):
	_write_article(
		tmp_path, 'loan-periods', 'Loan periods', 'Fourteen days is the standard loan.'
	)
	index_client, _ = _run(tmp_path, existing={ingest.INDEX_NAME})
	assert index_client.created == []


def test_ingest_uploads_one_doc_per_chunk_with_ids_and_vectors(tmp_path):
	_write_article(
		tmp_path,
		'loan-periods',
		'Loan periods and renewals',
		('Renewals are possible twice. ' * 200),  # ~1400 tokens → ≥2 chunks
	)
	_, search_client = _run(tmp_path)
	assert len(search_client.uploads) == 1
	docs = search_client.uploads[0]
	assert len(docs) >= 2
	ids = [doc['id'] for doc in docs]
	assert len(set(ids)) == len(ids), 'doc ids must be unique'
	for doc in docs:
		assert doc['id'].startswith('loan-periods-')
		assert doc['article'] == 'loan-periods'
		assert doc['title'] == 'Loan periods and renewals'
		assert isinstance(doc['chunk_index'], int)
		assert len(doc['content_vector']) == EMBED_DIMS


def test_ingest_reads_only_markdown_articles(tmp_path):
	_write_article(
		tmp_path, 'loan-periods', 'Loan periods', 'Fourteen days is the standard loan.'
	)
	tmp_path.joinpath('notes.txt').write_text('# Not an article\nshould be ignored')
	_, search_client = _run(tmp_path)
	docs = search_client.uploads[0]
	assert len(docs) == 1
	assert docs[0]['id'].startswith('loan-periods-')
	assert all('notes' not in doc['id'] for doc in docs)


def test_ingest_strips_markdown_syntax_from_content(tmp_path):
	_write_article(
		tmp_path,
		'damage-loss',
		'Damage and loss',
		'## Reporting\nReport **any damage** within `24 hours`.',
	)
	_, search_client = _run(tmp_path)
	content = search_client.uploads[0][0]['content']
	assert '##' not in content and '**' not in content and '`' not in content
	assert 'Report any damage within 24 hours.' in content


def test_ingest_merges_docs_from_all_articles(tmp_path):
	_write_article(
		tmp_path, 'loan-periods', 'Loan periods', 'Fourteen days is the standard loan.'
	)
	_write_article(tmp_path, 'asset-care', 'Asset care', 'Carry laptops in a sleeve.')
	_, search_client = _run(tmp_path)
	docs = search_client.uploads[0]
	assert {doc['article'] for doc in docs} == {'loan-periods', 'asset-care'}
