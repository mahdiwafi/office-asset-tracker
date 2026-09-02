# ADR 0004 — RAG assistant: retrieval, embeddings, generation

## Status

Accepted

## Context

Day 6 adds a staff-facing assistant that answers IT policy questions from the office's own help docs (`docs/help/`, six articles). The plan assumed Azure OpenAI for embeddings and generation. Availability check (2026-08-24) found the same governance family as ADR 0003: **free-trial subscriptions carry 0 TPM quota for all Azure OpenAI models** — any deployment fails with "Quota Not Met", regardless of the $200 credit. Azure AI Search Free tier is unaffected (50 MB, 3 indexes, 4096-dim vector cap, hybrid search with RRF, no semantic ranker — one free service per subscription).

## Decision

1. **Retrieval: Azure AI Search Free tier.** The index is defined in code (`app/assistant/search.py`), created idempotently by the ingest CLI (`uv run python -m app.assistant.ingest`). Queries are hybrid in one request: BM25 full-text plus a vector query, merged server-side by Reciprocal Rank Fusion, top-k = 10. The missing semantic ranker is accepted: hybrid + top-k is already above what a 10-chunk corpus needs, and the ranker's absence is documented rather than papered over.

    **Amendment (2026-08-25) — top-k raised from 5 to 10.** The Day 7 golden set caught a recall miss on its first real grading pass: for the projector-travel question, a top-k=5 pool let keyword overlap ("projector"/"workshop" hitting the eligibility article) crowd the correct asset-care chunk out of the pool, and the model refused honestly from evidence that should have been there. With a top-k=10 pool the correct chunk ranks 4th. Ten chunks cost ~4k prompt tokens on this corpus, and the model demonstrably ignores the chunks it does not cite — during golden-set grading it refused noise chunks three times in a row (citing [2] and [3] while the top-scored chunk was irrelevant). This is the manual-evaluation loop from ADR 0005 working as designed: a unit test cannot catch a retrieval miss, the golden set did.

2. **Embeddings: local fastembed (ONNX), BAAI/bge-small-en-v1.5, 384 dims.** No external embedding API: zero per-token cost, works offline, keeps tests hermetic, and 384 dims are far under the 4096-dim cap. The model is baked into the image at build time so the first query is instant.

3. **Generation: provider-neutral OpenAI-compatible chat completions, defaulting to DeepSeek `deepseek-v4-flash`**, env-gated on the presence of `LLM_API_KEY` — the same presence-is-config pattern as telemetry (Day 5). Without the key the endpoint returns retrieved citations with a `generation_configured: false` flag; adding the key later is a config change, not a code change. Grounding is enforced by prompt construction: numbered excerpts only, cite as [1]..[n], refuse when the excerpts don't answer. The wire contract (URL, auth header, JSON body) is pinned by a test.

    **Amendment (2026-09-02) — `deepseek-v4-flash`, not `deepseek-chat`.** The old `deepseek-chat` name no longer appears in DeepSeek's model list (`GET /models` returns `deepseek-v4-flash`, `deepseek-v4-pro`, and `deepseek-v4-flash-vision-exp`); the container app had no `LLM_MODEL` set, so it was silently running the stale default. The default was updated to `deepseek-v4-flash`, and `LLM_MODEL` is now set explicitly in the container-app environment so the live model is pinned rather than implicit. The wire contract remains unchanged — a model name is a config value, not code.

    **Amendment (2026-08-24) — DeepSeek, not Claude.** The first live deploy returned 500s: the key in the container's `ANTHROPIC_API_KEY` slot was a DeepSeek key, which Anthropic's API correctly rejects (401) — keys are scoped to their issuing provider, never interchangeable. Rather than fund a new Anthropic account, the plan's own fallback clause (docs/plan.md: "any hosted LLM API for generation while keeping Azure AI Search for retrieval — the architecture doesn't change") was invoked: generation now speaks OpenAI-compatible chat completions over plain `httpx` — the same wire format DeepSeek, OpenAI and Azure OpenAI all accept — with the provider a base URL and model name away (`LLM_BASE_URL`, `LLM_MODEL`; defaulted to api.deepseek.com / deepseek-chat at the time). Claude remains a drop-in: reintroduce an Anthropic-compatible adapter and swap the env vars. The Anthropic SDK dependency was removed. Generation is now best-effort: a failed model call degrades to citations, never a 500.

4. **[CP] Chunking: ≈400 tokens, 10% overlap** — the candidate's decision (2026-08-24). 400 tokens is roughly one policy paragraph: small enough that a chunk answers one question, large enough that an answer rarely spans chunks; 1–3 chunks per article. 10% overlap carries a sentence tail into the next chunk so a question straddling a boundary still finds both halves, at negligible cost on a 50 MB budget. Two hard invariants implemented in `app/assistant/chunking.py`: chunks are sentence-complete (a cut sentence destroys retrieval for both halves), and a trailing chunk under 40% of the target merges back into the previous one — dropping its carried overlap prefix so the merge duplicates nothing.

## Consequences

- The six-article corpus chunks to roughly ten documents; the free tier's 50 MB / 3-index limits are ample and cost nothing.
- Generation depends on an API key outside Azure, paid per token (~a fraction of a cent per answer). Handover note: the key lives in the container-app environment, never in the repo.
- Azure OpenAI can be swapped in later — for embeddings and generation both — without touching the retrieval contract: the vector field dimensions and the search client are provider-agnostic. The architecture survives the quota wall in either direction.
- The frontend (Day 7) gets citations (article, chunk, excerpt, score) on every response, so the assistant is never a black box.
