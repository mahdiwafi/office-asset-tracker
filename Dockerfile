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

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

# Migrations (and the idempotent demo seed) run at container boot, not
# build: the image is built in CI where the database is unreachable.
# Same pattern as the App Service startup command, minus the platform.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
