# Azure AI Search wiring: client factory and the help-docs index schema.
#
# The index is defined in code, not in the portal — the schema is versioned
# with the pipeline that feeds it, and a fresh environment can be rebuilt
# from nothing with one command. Free tier limits (50 MB storage, 3
# indexes, no semantic ranker) are ample for this corpus; the missing
# semantic ranker is why we rely on hybrid retrieval rather than
# pure-keyword ranking (ADR 0004).
import azure.core.credentials
import azure.core.exceptions
import azure.search.documents
import azure.search.documents.indexes
import azure.search.documents.indexes.models
import azure.search.documents.models

from app.assistant import AssistantNotConfigured
from app.core.config import settings

INDEX_NAME = 'help-docs'
# Must match the embedding model (fastembed BAAI/bge-small-en-v1.5) and
# stay under the free tier's 4096-dimension vector cap.
EMBEDDING_DIMENSIONS = 384
VECTOR_PROFILE = 'help-vector-profile'


def build_index(
	name: str = INDEX_NAME,
) -> azure.search.documents.indexes.models.SearchIndex:
	fields = [
		azure.search.documents.indexes.models.SimpleField(
			name='id',
			type=azure.search.documents.indexes.models.SearchFieldDataType.String,
			key=True,
		),
		azure.search.documents.indexes.models.SearchableField(
			name='title',
			type=azure.search.documents.indexes.models.SearchFieldDataType.String,
			searchable=True,
			filterable=True,
		),
		azure.search.documents.indexes.models.SearchableField(
			name='article',
			type=azure.search.documents.indexes.models.SearchFieldDataType.String,
			filterable=True,
		),
		azure.search.documents.indexes.models.SimpleField(
			name='chunk_index',
			type=azure.search.documents.indexes.models.SearchFieldDataType.Int32,
			filterable=True,
		),
		azure.search.documents.indexes.models.SearchableField(
			name='content',
			type=azure.search.documents.indexes.models.SearchFieldDataType.String,
			searchable=True,
		),
		azure.search.documents.indexes.models.SearchField(
			name='content_vector',
			type=azure.search.documents.indexes.models.SearchFieldDataType.Collection(
				azure.search.documents.indexes.models.SearchFieldDataType.Single
			),
			searchable=True,
			vector_search_dimensions=EMBEDDING_DIMENSIONS,
			vector_search_profile_name=VECTOR_PROFILE,
		),
	]
	vector_search = azure.search.documents.indexes.models.VectorSearch(
		algorithms=[
			azure.search.documents.indexes.models.HnswAlgorithmConfiguration(
				name='help-hnsw',
				parameters=azure.search.documents.indexes.models.HnswParameters(
					metric=azure.search.documents.indexes.models.VectorSearchAlgorithmMetric.COSINE
				),
			)
		],
		profiles=[
			azure.search.documents.indexes.models.VectorSearchProfile(
				name=VECTOR_PROFILE, algorithm_configuration_name='help-hnsw'
			)
		],
	)
	return azure.search.documents.indexes.models.SearchIndex(
		name=name, fields=fields, vector_search=vector_search
	)


def create_index_if_missing(
	index_client: azure.search.documents.indexes.SearchIndexClient,
) -> None:
	"""Create the index on first ingest; no-op afterwards. The re-ingest
	path is idempotent: run it after every article edit."""
	try:
		index_client.get_index(INDEX_NAME)
	except azure.core.exceptions.ResourceNotFoundError:
		index_client.create_index(build_index())


def _clients() -> tuple[
	azure.search.documents.indexes.SearchIndexClient,
	azure.search.documents.SearchClient,
]:
	"""Fresh client pair from settings. Presence of the endpoint IS the
	configuration flag — the router 503s before this is ever reached."""
	if not settings.ai_search_endpoint or not settings.ai_search_key:
		raise AssistantNotConfigured(
			'set AI_SEARCH_ENDPOINT and AI_SEARCH_KEY to use the assistant'
		)
	credential = azure.core.credentials.AzureKeyCredential(settings.ai_search_key)
	index_client = azure.search.documents.indexes.SearchIndexClient(
		settings.ai_search_endpoint, credential
	)
	search_client = azure.search.documents.SearchClient(
		settings.ai_search_endpoint, settings.ai_search_index, credential
	)
	return index_client, search_client
