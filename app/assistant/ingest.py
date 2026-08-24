# The ingest pipeline: upload → chunk → embed → index.
#
# Reads every markdown file in docs/help/, chunks it (400 tokens / 10%
# overlap), embeds each chunk locally, and pushes the documents to Azure
# AI Search. Idempotent: run it again after editing an article and the
# index converges (upload_documents upserts by id).
#
# Usage: uv run python -m app.assistant.ingest
# Requires AI_SEARCH_ENDPOINT and AI_SEARCH_KEY in the environment.
import dataclasses
import pathlib
import re

from app.assistant.chunking import chunk_text
from app.assistant.embeddings import embed_texts
from app.assistant.search import INDEX_NAME, _clients, create_index_if_missing

HELP_DIR = pathlib.Path(__file__).resolve().parents[2] / 'docs' / 'help'


@dataclasses.dataclass(frozen=True)
class Article:
	title: str
	slug: str
	content: str


def _plain(text: str) -> str:
	"""Strip the markdown we know how to read: heading markers, bold,
	code backticks. Everything else passes through."""
	text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
	return text.replace('**', '').replace('`', '').strip()


def load_articles(help_dir: pathlib.Path = HELP_DIR) -> list[Article]:
	"""Read docs/help/*.md. The H1 becomes the title; the rest of the file
	is chunked verbatim (minus markdown syntax)."""
	articles: list[Article] = []
	for path in sorted(help_dir.glob('*.md')):
		raw = path.read_text(encoding='utf-8')
		title_match = re.match(r'^#\s+(.+)$', raw, flags=re.MULTILINE)
		title = title_match.group(1) if title_match else path.stem
		articles.append(Article(title=title, slug=path.stem, content=_plain(raw)))
	return articles


def run_ingest(
	*,
	help_dir: pathlib.Path = HELP_DIR,
	embedder=embed_texts,
	index_client,
	search_client,
) -> int:
	"""Chunk, embed and upload every article. Returns the number of chunks
	indexed. All external calls are injectable so tests run hermetically."""
	create_index_if_missing(index_client)
	chunks: list[tuple[Article, int, str]] = []
	for article in load_articles(help_dir):
		for index, text in enumerate(chunk_text(article.content)):
			chunks.append((article, index, text))
	vectors = embedder([text for _, _, text in chunks])
	documents = [
		{
			'id': f'{article.slug}-{index}',
			'title': article.title,
			'article': article.slug,
			'chunk_index': index,
			'content': text,
			'content_vector': vector,
		}
		for (article, index, text), vector in zip(chunks, vectors)
	]
	search_client.upload_documents(documents)
	return len(documents)


def main() -> None:
	index_client, search_client = _clients()
	count = run_ingest(index_client=index_client, search_client=search_client)
	print(f'indexed {count} chunks into {INDEX_NAME}')


if __name__ == '__main__':
	main()
