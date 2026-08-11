# CLAUDE.md — Office Asset & Request Tracker

## Stack

Python 3.12+ · FastAPI · SQLAlchemy 2 async + asyncpg · Alembic · Pydantic v2 / pydantic-settings · uv · ruff · pytest + pytest-asyncio + httpx. Frontend (day 5): Next.js App Router.

## Layer boundaries

- **Routers are thin.** Handlers parse the request, delegate to a service, map result to a response schema. No business rules in routes.
- **Rules live in services.** Loan overlap, approval chains, reconciliation — everything testable lives in `app/services/`.
- **Schemas stay separate from ORM models.** Request, response, and DB models are distinct Pydantic classes; never expose ORM models in responses.
- **Config comes from the environment** (`app/core/config.py`, pydantic-settings). No secrets in code, no defaults that work only on one machine.

## Commands

- Tests: `uv run pytest`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Migration: `uv run alembic upgrade head` / `uv run alembic revision --autogenerate -m "msg"` (see `.claude/skills/db-migrations.md`)
- Run: `uv run uvicorn app.main:app --reload`

## House style

- **Tabs** for indentation, **single quotes**, no trailing whitespace.
- **Full module imports** — `import sqlalchemy`, `import sqlalchemy.orm as saorm` — never `from sqlalchemy import ...` for package-level names.
- **No blank lines inside function bodies.**
- **Annotate module-level signatures only** — functions/classes annotated; locals inferred.

## Workflow rules

- TDD: failing test first, always — see `.claude/skills/tdd-workflow.md`.
- Fundamentals checkpoints are marked `[CP]` in `docs/plan.md`. At a checkpoint, do not implement — follow `.claude/skills/teaching-mode.md`.
- Architectural choices get an ADR — see `.claude/skills/adr.md`.
- Keep README and ADRs updated as work lands; documentation written at the end is documentation that doesn't get written.
