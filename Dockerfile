# Runtime image for the API, hosted on Azure Container Apps.
#
# Single stage on purpose: the dependency set is small, and a simpler
# Dockerfile is a Dockerfile the candidate can explain line by line.
#
# The image carries NO secrets. DATABASE_URL and the Entra settings
# arrive as container-app environment variables at deploy time — the
# image is public on GHCR by design, so anything baked in would leak.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# requirements.txt is `uv export --no-dev` — hashes pinned, pip-installable.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image: without this, the first
# /assistant/query after a deploy pays a ~100 MB model download from
# Hugging Face. The name must match EMBEDDING_MODEL (the default in
# app/core/config.py), and the download lands in ~/.cache/fastembed —
# which is also the runtime default cache_dir, so queries find the
# baked model with zero configuration.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY docs/help ./docs/help

# Migrations (and the idempotent demo seed) run at container boot, not
# build: the image is built in CI where the database is unreachable.
# Same pattern as the App Service startup command, minus the platform.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
