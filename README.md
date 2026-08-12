# Office Asset & Request Tracker

Internal tool for a small organisation: track equipment, handle loan and return requests through an approval workflow, and answer staff questions about IT policy from its own help docs.

![CI](https://github.com/mahdiwafi/office-asset-tracker/actions/workflows/ci.yml/badge.svg)

## Stack

- **Backend** — Python + FastAPI (SQLAlchemy 2 async, Alembic)
- **Frontend** — Next.js (App Router) *(day 5)*
- **Database** — PostgreSQL
- **Auth** — Microsoft Entra ID (OIDC / MSAL) *(day 4)*
- **AI** — Azure AI Search retrieval + hosted LLM generation *(day 6)*
- **Hosting** — Azure App Service
- **CI/CD** — GitHub Actions · **Observability** — Application Insights

## Quick start

```sh
docker compose up -d          # Postgres
cp .env.example .env          # config comes from the environment
uv sync                       # install locked deps
uv run pytest                 # run the test suite
uv run uvicorn app.main:app --reload
```

## Migrations

```sh
uv run alembic upgrade head
```

## Design notes

See `docs/adr/` for architectural decisions and `docs/plan.md` for the build schedule.
