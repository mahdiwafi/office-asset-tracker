# Build plan — Office Asset & Request Tracker

The product: an internal tool for a small organisation — track equipment, handle loan/return requests through an approval workflow, and answer staff questions about IT policy from its own help docs.

**This plan has two outputs.** The deployed artifact, and a set of backend fundamentals the candidate can explain under questioning. A project they can demo but not explain is worth very little. Checkpoints marked **[CP]** are stop-and-hand-back points (see `.claude/skills/teaching-mode.md`) — budget them generously; they are the deliverable.

**The split that makes the schedule viable.** The agent writes scaffolding, CRUD routes, form components, migration boilerplate, styling. The candidate writes every test and does every checkpoint by hand. If that inverts to save time, the week produces a demo they cannot defend.

## Day 1 — Foundations and domain rules

| Hours | Work |
| --- | --- |
| 0.5 | Repo, `uv` init, `ruff` pinned with house config, Docker Compose Postgres |
| 1.0 | `pytest` + `httpx` wired, `/health` endpoint that actually checks the DB, first test passing |
| 1.0 | GitHub Actions running lint + tests on push, badge in README |
| 0.5 | ADR 0001 — stack selection |
| 1.5 | **[CP]** Write the Phase 1 test list by hand. All nine names, as failing tests. No implementation. |
| 3.5 | SQLAlchemy models, Alembic initial migration, Pydantic schemas — agent implements against those tests |

**End state:** CI green, domain tests failing for the right reasons, models in place.

**Concepts:** why a health check that ignores the DB is worse than none; lockfiles vs version ranges; why config comes from the environment; why a broken `main` must be immediately visible.

## Day 2 — Business rules and the concurrency lesson

| Hours | Work |
| --- | --- |
| 3.0 | Service layer implementing the loan/request/approval rules until the test list is green |
| 2.0 | **[CP]** The race condition. Reproduce double-booking with two parallel requests against the passing test. Watch it fail. |
| 1.5 | **[CP]** Fix it properly — exclusion constraint on the loan range, or `SELECT ... FOR UPDATE`. Candidate decides and justifies which. |
| 1.0 | **[CP]** Transaction boundary on approval: four writes, all or nothing. Break it deliberately with an exception mid-way, observe rollback. |
| 0.5 | ADR 0002 — concurrency control choice |

**End state:** domain logic correct under concurrency, not just under test.

**Concepts:** why application-level checks are insufficient; atomicity; append-only audit trails; rules in the service layer, not the routes.

This is the highest-value day in the week. Do not compress it to catch up on something else.

## Day 3 — API layer

| Hours | Work |
| --- | --- |
| 1.0 | **[CP]** Status code design. Candidate maps each failure mode to a code and defends it — double-booking is 409, not 400. |
| 2.5 | Routers per concern, thin handlers delegating to services, request/response schemas kept separate from ORM models |
| 1.5 | HTTP-level tests via `httpx.AsyncClient`, DB in a per-test transaction |
| 1.0 | **[CP]** N+1 diagnosis. Turn on SQLAlchemy echo, load the loan list, count the queries. Fix with eager loading. Add an FK index, compare `EXPLAIN ANALYZE` before and after. |
| 1.0 | Pagination on list endpoints |
| 1.0 | Idempotency key on request creation |

**End state:** tested API, OpenAPI docs generated, no obvious query pathologies.

**Concepts:** status codes as contract; idempotency; statelessness; validation at the boundary; why exposing ORM models leaks internals.

## Day 4 — Entra ID SSO

| Hours | Work |
| --- | --- |
| 1.0 | App registration in Entra ID, redirect URIs, app roles |
| 1.5 | **[CP]** Decode a real token at jwt.io. Candidate explains `iss`, `aud`, `exp`, `nbf` and what each prevents, before any validation code is written. |
| 2.0 | **[CP]** JWT validation against JWKS, written by the candidate with the agent reviewing rather than authoring |
| 1.5 | Auth tests with mocked JWKS and locally minted tokens — deterministic, no network in CI |
| 1.5 | **[CP]** Authorisation layer: role check enforced server-side on every protected endpoint. Candidate audits each route themselves. |
| 0.5 | User provisioning on first login from token claims |

**End state:** real OIDC, verified server-side, role-based access enforced.

**Concepts:** authentication vs authorisation; asymmetric signing and why the API holds no minting secret; PKCE; access vs refresh tokens; where secrets live in production and what to do when one leaks.

## Day 5 — Frontend and deploy

| Hours | Work |
| --- | --- |
| 3.5 | ✅ Next.js App Router, MSAL React login, six screens — asset list, asset detail, raise request, approval queue, my loans, audit log. Functional, restrained styling. Agent leads. |
| 1.0 | ✅ Azure Container Apps + Azure Database for PostgreSQL provisioned, budget alert set at $50; frontend containerized and deployed (hosting deviation — free trial blocks App Service, see ADR 0003) |
| 2.0 | ✅ **[CP]** First deploy, and the failures it produced: `btree_gist` allow-list on Azure Postgres; consumer-account sign-in wall in a fresh tenant; Web-vs-SPA platform mismatch (AADSTS9002326). Candidate debugged all three. |
| 1.0 | ✅ GitHub Actions deploying on merge to `main`; Application Insights wired via env-gated OpenTelemetry — telemetry verified in portal queries |
| 0.5 | ✅ Scale to two instances — concurrent boot is safe (Alembic advisory lock); telemetry proves both replicas serve traffic |

**End state: a public URL — achieved.** The single highest-value artifact — nothing in the candidate's history currently proves they can operate a deployed system. The URL is live and login-gated; the assets list renders seeded rows from Postgres through an Entra-issued token.

**Concepts:** environment parity and why it is never perfect; connection pooling against a capped managed DB; migrations in a pipeline; structured logging you can query; what statelessness bought them; cloud cost as an engineering constraint.

## Day 6 — RAG assistant

| Hours | Work |
| --- | --- |
| 2.0 | ✅ Six help articles written for non-technical readers — `docs/help/`: requesting equipment, loan periods & renewals, damage & loss, offboarding returns, eligibility & priority, asset care. 2,673 words. |
| 1.0 | ✅ Availability verified by search: **Azure OpenAI is quota-blocked on free trials (0 TPM — same wall as App Service, ADR 0003 family)**; AI Search Free tier confirmed (50 MB, 3 indexes, vector ≤4096 dims, hybrid RRF, no semantic ranker). Generation = **provider-neutral OpenAI-compatible chat completions, defaulting to DeepSeek `deepseek-chat`** — first live deploy 500'd when the `ANTHROPIC_API_KEY` slot held a DeepSeek key (keys are provider-scoped), and the plan's fallback clause was invoked: `LLM_API_KEY` + base URL + model, Claude a drop-in adapter swap. Live retrieval verified against the real service (5 citations). See ADR 0004. |
| 1.5 | ✅ **[CP]** Chunking — candidate picked **≈400 tokens / 10% overlap** (2026-08-24) and justified against the trade-off table: paragraph-sized chunks fit one answer, 1–3 chunks/article; 10% overlap insures boundary-straddling questions at negligible cost. Sentence-complete invariants enforced. |
| 2.0 | ✅ Upload → chunk → embed → index pipeline (`app/assistant/{chunking,embeddings,search,ingest}.py`), CLI `uv run python -m app.assistant.ingest`, idempotent (index-as-code, upsert by id), every SDK call mocked in tests. |
| 1.5 | ✅ Hybrid query (BM25 + vector, RRF-merged) with top-k=5, citations built from every response (article, chunk, excerpt, score), grounded generation env-gated on `ANTHROPIC_API_KEY` — absent → citations-only, app still works. 25 new tests, all hermetic. |

**End state:** working retrieval and generation, tested with mocks — **achieved and verified live (2026-08-24):** AI Search Free provisioned, 11 chunks ingested from the container console, `POST /assistant/query` returns a grounded DeepSeek answer with 5 citations in ~7s. The first live query 500'd (Anthropic slot held a DeepSeek key — keys are provider-scoped); fixed by the provider-neutral adapter and verified. Finding carried to Day 7: 200-char excerpts truncate mid-word and the model had to refuse part of the answer — excerpt length and word-bounding belong with the cited-sources UI (resolved in Day 7 row 2: evidence and display are now separate artifacts).

**Concepts:** embeddings as semantic coordinates; why hybrid beats pure vector on short factual queries; why the Free tier's missing semantic ranker matters.

## Day 7 — Refusal path, packaging, rehearsal

| Hours | Work |
| --- | --- |
| 1.5 | ✅ **[CP]** Score threshold and refusal — candidate chose **floor 0.020 + model referee**, justified against a 16-query live score battery (2026-08-24): every real-word query scored ≥0.0315, pure nonsense 0.0167, and RRF scores proved uncalibrated ("capital of France" 0.0328 — a score-only threshold is dead on arrival). Below the floor: deterministic refusal, no model call. Above it: the model refuses semantic mismatches via the system prompt. Response gains `refused: true`; weak evidence still returned. 103 tests. |
| 1.5 | ✅ Cited-sources UI — Ask ICT page (`frontend/app/assistant`): grounded answer with clickable [n] citation markers, the refusal state shown honestly, and every source card (title, chunk, match score, excerpt) linked to its article in the public repo — most junior RAG projects are black boxes. The carried Day 6 excerpt fix landed with it: the model now gets FULL chunk content (evidence artifact) while the UI shows word-bounded truncations that say so (display artifact) — the mid-word 200-char cut that made the model infer "days" is gone. 105 tests. |
| 1.0 | Ten-pair golden set, evaluated manually. ADR noting that probabilistic behaviour cannot be unit-tested. |
| 1.5 | README — problem, architecture diagram, live URL, screenshots, testing approach, what changes at scale |
| 1.0 | Three-minute screen recording of real usage, not a code tour |
| 1.5 | **[CP]** Full interview rehearsal. Agent interrogates every decision across the week and reports which answers were weak. |

**End state:** deployed, documented, defensible.

## If the week slips

Cut in this order: the cited-sources UI, then the golden set, then the RAG feature entirely. **Stop at Day 5 if you must** — a deployed, authenticated, tested fullstack app with a real concurrency fix is already a stronger artifact than most junior portfolios.

**Never cut:** the Day 2 concurrency work, the Day 4 authorisation audit, or the Day 7 rehearsal. Those are what convert the project from a demo into an interview.

## Azure cost warning

The $200 credit expires 30 days after activation and cannot be paused.

- **Azure AI Search Basic tier is roughly $75/month** and will eat the credit fast. Use the **Free tier** (50 MB, 3 indexes, no semantic ranker) — ample for a 12-document corpus. Note the semantic ranker absence in the ADR; it is a real limitation and knowing it exists is a good signal.
- **LLM availability varies by region and has had approval gates.** Verify access before designing around it. Fallback: any hosted LLM API for generation while keeping Azure AI Search for retrieval — the architecture doesn't change.

Set a budget alert at $50 on day one.

## Learning discipline — read before starting

- **Write the tests by hand.** All of them. The test names in Phase 1 are the specification. Let the agent implement against tests the candidate wrote; never the reverse.
- **Never accept code they cannot explain line by line.** The honest check: could they delete a generated file and rewrite it from memory in rough form? If not, they have a dependency, not a skill.
- **Do the hard parts manually, at least once.** The race condition fix, the JWT validation, the chunking logic. These are the three things an interviewer will actually probe.
- **Keep a `docs/learning-log.md`.** One entry per session: what was built, what broke, what the fix was, and one thing understood that wasn't understood that morning. Ten minutes a day.
- **Interview rehearsal at the end of each phase.** Claude Code acts as a technical interviewer against the code just written. Any question that produces a shaky answer marks a concept to go back and learn.

The measure of success is not the deployed app. It is whether the candidate can sit in a room and explain why the loan table has an exclusion constraint.
