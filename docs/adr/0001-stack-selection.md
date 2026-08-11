# ADR 0001 — Stack selection

## Status

Accepted

## Context

The portfolio needs one deployed, credible product that serves both general fullstack applications and AI-enabled/ICT roles — not two disconnected repos. The candidate has a fullstack background (.NET, Node/Express, React/Next.js, PostgreSQL, MongoDB) and one month of Azure credit. The product must demonstrate: relational integrity under real business rules, authentication, deployment on Azure, and one AI-enabled feature — all within a one-week build, using Claude Code as the implementation agent with the candidate writing tests and checkpoints by hand.

## Decision

- **Backend:** Python + FastAPI, SQLAlchemy 2 async + asyncpg, Alembic
- **Frontend:** Next.js (App Router)
- **Database:** PostgreSQL — locally via Docker Compose, in Azure via Database for PostgreSQL Flexible Server (Burstable B1ms)
- **Auth:** Microsoft Entra ID (OIDC / MSAL) — the org context is a Microsoft 365 shop
- **Vector store / retrieval:** Azure AI Search (Free tier — Basic is ~$75/month and would eat the credit)
- **Generation:** hosted LLM API (see consequences — provider has approval gates; fallback preserves the architecture)
- **Hosting:** Azure App Service (backend + frontend)
- **CI/CD:** GitHub Actions, deploying on merge to `main`
- **Observability:** Application Insights
- **Dependency management:** `uv` (lockfile reproducibility; CI uses `uv sync --frozen`)
- **Testing:** pytest + pytest-asyncio + httpx; TDD throughout

## Consequences

- Python/FastAPI trades the candidate's existing .NET familiarity for a backend ecosystem worth having on a CV — FastAPI's automatic OpenAPI docs, Pydantic validation at the boundary, and async support map directly to the app's concurrency story.
- SQLAlchemy async + asyncpg is the steeper part of the stack; that is intentional — the loan-overlap concurrency lesson (Day 2) is the project's centerpiece and cannot be taught on a stack that hides locking.
- Entra ID SSO costs real setup time but matches the target organisation's Microsoft 365 context and demonstrates OIDC competence rather than a toy username/password table.
- Azure AI Search Free tier is ample for a 12-document corpus but lacks the semantic ranker; retrieval quality relies on hybrid (keyword + vector) queries instead.
- Generation provider is not yet fixed: Azure OpenAI availability varies by region and has had approval gates. Any hosted LLM API can back the generation step while Azure AI Search stays the retrieval layer — the architecture does not change.
- A budget alert at $50 is set on day one; the $200 credit cannot be paused, so spending discipline is a design constraint, not an afterthought.
