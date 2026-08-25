# Learning log

First-person notes on what each checkpoint actually taught me. Written
after the fact, in my own words — the point is to be able to *explain*
these under questioning, not just to have done them.

## 2026-08-11 → 2026-08-14 — Day 1: foundations

The repo, the rules, and the first failing tests. The house style came
first: `uv` for dependency management, ruff pinned to a fixed version,
tabs and single quotes — and formatting is CI-enforced, so a format
failure is a hard CI failure, not a suggestion. Docker Compose Postgres
for local development, pytest + httpx wired, and a `/health` endpoint
that actually checks the database: a health check that ignores the DB
is worse than none, because it reports "healthy" while the app is down.

The checkpoint: write the Phase 1 test list by hand — the spec tests,
as failing tests, with no implementation. That list is the
specification. The agent implements against tests I wrote, never the
reverse. The tests sat red (marked `xfail`) for three days while the
SQLAlchemy models, the initial Alembic migration and the Pydantic
schemas landed, and the service layer grew the eleven domain rules —
unique inventory tag, max loan duration, the hard-delete guard — until
the suite went green. CI ran lint + tests on every push from day one,
with a badge in the README, so a broken main was visible in minutes.

**Test yourself:** what does a hard format-check gate protect? Why does
the health check touch the database? What makes a list of failing test
names a specification?

## 2026-08-18 → 2026-08-19 — Day 2: the race condition

The most valuable day of the week. Two people request the same asset
for overlapping dates, at the same time. The service layer already had
a test saying each request succeeds individually — and two parallel
requests both succeeded against that passing test. Double-booking,
live.

**Why the application-level check is insufficient:** both requests read
the loan table, both saw "free", both wrote. Two sequential reads never
collide; two interleaved reads both pass the check. There is no amount
of code-side caution that fixes this — the check and the write must be
atomic in the database itself.

**The fix, and why I chose it:** an exclusion constraint —
`EXCLUDE USING gist (asset_id WITH =, daterange(start_date, due_date)
WITH &&)` — so the database refuses overlapping loans for the same
asset at the storage layer (ADR 0002). I weighed `SELECT ... FOR
UPDATE` and rejected it: the lock works, but *every* future write path
must remember to take it, and a missed one silently re-opens the race.
The constraint cannot be forgotten. The cost is Postgres-only (the
`btree_gist` extension) — a cost that would come back to bite me on
Day 5, when Azure's managed Postgres needed the extension
allow-listed.

**The approval transaction:** an approval is four writes — the approval
row, the request status, the loan, the audit trail. I deliberately
threw an exception after the third write and watched the rollback: all
or nothing, or the audit trail would lie about what happened.

**Test yourself:** why is an application-level availability check
insufficient? Why an exclusion constraint over row locks? What does
"append-only audit trail" mean, and why must the approval write to it
in the same transaction?

## 2026-08-19 → 2026-08-20 — Day 3 + 4: the API layer, then Entra ID

**Day 3 (08-19) — the API as a contract.** Routers per concern with
thin handlers; Pydantic request/response schemas kept separate from ORM
models (the API must not leak the database's shape). Status codes
mapped failure mode by failure mode and defended: double-booking is
**409 Conflict** — the request is well-formed, the resource state
collides — not 400. HTTP-level tests through the real ASGI app over a
per-test transaction. I diagnosed an N+1: with SQLAlchemy echo on, the
loan list emitted one query per loan. Eager loading collapsed it to
one. Added an FK index and compared `EXPLAIN ANALYZE` before and after.
Pagination with a shared envelope, and an idempotency key on request
creation: the client sends a key, and a retried request does not create
a second row.

**Day 4 (08-20) — tokens and who trusts what.** I decoded a real access
token at jwt.io before writing any validation code: `iss` (which tenant
minted it — rejects tokens from other tenants), `aud` (which app it is
meant for — rejects tokens stolen for a sibling app), `exp`/`nbf` (the
time window). Validation is JWKS-based: the API holds only the signing
public keys, never the minting secret — if the secret leaked, it could
not sign tokens. Tests use a mocked JWKS and locally minted tokens, so
the suite is deterministic with no network. Then I audited every
protected route myself: the role check is server-side, enforced by the
API, not by hiding buttons in the UI.

**Test yourself:** 409 vs 400 — what is the difference and why does it
matter to API clients? What does the server store for an idempotency
key? Why is `exp` useless without `aud`? Why does the API hold no
signing secret, and what does it hold instead?

## 2026-08-22 — Day 5: the three-walled first login

The app was deployed: two Azure Container Apps, images in GHCR, CI green,
the API healthy. Then I spent the better part of a day trying to sign in
through the browser. Three separate walls, each one a different layer, and
each one only visible after the previous one was removed.

### Wall 1 — the account itself (the "We couldn't sign you in" loop)

**Symptom:** the app redirected to Microsoft, and the sign-in page looped
between `authorize` and `reprocess` with a generic "We couldn't sign you
in. Please try again." — no error code, no details.

**What I tried first (and why it was the wrong layer):** browser fixes —
incognito, another window, clearing cookies. All useless, which was the
first real clue: a config problem wouldn't care about the browser.

**What actually worked:** we replayed the exact authorize request the app
was making (curl, with the real PKCE challenge from the URL bar) and got a
clean sign-in page back — *no error*. That proved the request, the app
registration, the redirect URI and the scope were all valid. So the
failure was inside Entra's session handling, and the error page finally
named it: the account shown was `teiiforbat@outlook.com` — a **consumer
Microsoft account**. My tenant was created from a personal Outlook
account, and that consumer identity can sign into the Azure portal (it
gets a special path there) but cannot complete a normal OIDC sign-in
against the workforce directory. The tenant's user list said `Users: 1` —
there was literally no directory user that could sign in. **Fix:** create
a real user (`wafi@teiiforbatoutlook.onmicrosoft.com`), sign in with it.

**Lesson:** the browser session is the *last* thing to blame, not the
first. The bisect that worked was replaying the request server-side to
prove the config layer, then reading the error page for the identity it
named. Also: a free-trial Azure tenant is founded on a consumer account,
and that account is not a directory user — know which identity your app
expects before debugging anything else.

### Wall 2 — Web platform vs SPA platform (AADSTS9002326)

**Symptom:** after the new user worked, sign-in succeeded but the app
bounced straight back to the login page. Console showed the token
exchange POST failing with **400**.

**The trap:** at every earlier stage the request was valid — authorize
passed, sign-in passed, the code came back to the app. Only the final
leg, the code-for-token exchange, failed, and only in a browser. A
server-side replay could never see it: the failure was a *cross-origin*
check.

**Root cause:** I had registered the redirect URI under the **Web**
platform of the app registration. That makes Entra treat the app as a
confidential client. But MSAL.js is a public client doing the SPA flow
(PKCE, code exchanged from the browser origin). Entra's token endpoint
answered `AADSTS9002326: Cross-origin token redemption is permitted only
for the 'Single-Page Application' client-type.` **Fix:** add the same
redirect URIs under a **Single-page application** platform instead.

**Lesson:** the platform type in the app registration is not decoration —
it selects the client type, and the client type decides which flows the
token endpoint will accept. Web ≠ SPA. This is a one-word config error
whose failure only surfaces at the last hop, in a browser, with a 400
that a scripted test would miss.

### The method, generalised

1. Prove the request (replay it) before debugging the environment.
2. Prove the config layer before blaming the browser.
3. When the failure needs a browser to reproduce, the console and the
   Network tab's *response body* are the evidence — the error JSON named
   the exact AADSTS code.
4. Each wall was invisible until the previous one fell: consumer account
   → directory user → then the platform mismatch surfaced. Debug the
   layers in order, and the error pages will keep naming the next one.

### Interview takeaway

The sequence I can now tell from memory, with the receipts: replayable
authorize request, tenant with one consumer account, `Users: 1`, and the
9002326 response body that named the fix. That is a complete story about
how Entra classifies clients — worth more than a paragraph of theory.

## 2026-08-21 → 2026-08-23 — Day 5, continued: the deployment machinery

The login walls above are one part of Day 5; here is the machinery
behind them. Azure App Service is quota-blocked on the free trial, so
the deployment runs on Azure Container Apps: Dockerfiles for both
services, images pushed to GHCR by a GitHub Actions workflow, and a
deploy job that swaps the images into the container apps on every merge
to main. ADR 0003 records the hosting deviation and why.

The first deploy failed — and the cause reached all the way back to Day
2: the `btree_gist` extension is not allow-listed on Azure Database for
PostgreSQL by default, so the migration that creates the exclusion
constraint could not run. Fix: enable the extension on the managed
instance.

Telemetry came via Application Insights with OpenTelemetry, env-gated —
the same presence-is-config pattern used everywhere else: no connection
string, no telemetry. Then scale-out to two instances: concurrent boot
is safe because the Alembic migration is protected by an advisory lock
(only one instance migrates), and the telemetry proved both replicas
served traffic. A single container can no longer crash the app.

**Test yourself:** why does the migration need the extension
allow-listed? What exactly does the advisory lock protect? What does
env-gated telemetry mean, and why does a stateless API scale to two
instances safely?

## 2026-08-24 — Day 6: the RAG assistant

Six help articles became a searchable, answerable corpus. The pipeline:
upload → chunk → embed → index. The chunking decision (mine): ~400
tokens per chunk, 10% overlap, sentence-complete — a cut sentence
destroys retrieval for both halves. Retrieval is hybrid: BM25 keyword
search plus a vector query in one request, merged server-side by
Reciprocal Rank Fusion — it merges *ranks*, not scores, which is why
the scores are all squeezed into 0.03 and cannot be read as relevance.
Embeddings are local (fastembed, 384 dims) — no embedding API, and the
tests stay hermetic.

Generation is provider-neutral: OpenAI-compatible chat completions over
plain httpx, with the provider a base URL and model name away. The
first live query taught me why: it 500'd because the `ANTHROPIC_API_KEY`
slot held a DeepSeek key. Keys are scoped to their issuing provider —
never interchangeable. The fix made the wire format the contract, not
the vendor. Generation is best-effort: if the model call fails, the
endpoint degrades to citations, never a 500.

Evidence vs display: a raw 200-character cut truncated mid-word, and
the model had to guess the rest ("the standard loan period is 14 d…").
Now the model receives full chunk content, and the UI shows
word-bounded excerpts that signal truncation with "…".

**Test yourself:** why hybrid over pure vector for short factual
questions? What exactly does RRF merge — and what does that imply about
reading the match scores? Why are chunks sentence-complete? What does
the provider-neutral adapter send on the wire?

## 2026-08-24 → 2026-08-25 — Day 7: the golden set caught a real bug

Day 7 ran across two calendar days: the refusal path, the golden set,
the README and the recording script landed on 08-24; the top-k finding,
the live 10/10 grading and the frontend redesign on 08-25.

Two-stage refusal: a 0.020 score floor refuses deterministically with
no model call (pure nonsense scores 0.0167); above the floor, the model
refuses semantic mismatches itself. The score battery proved a
score-only threshold is dead on arrival: "capital of France" scored
0.0328 — *above* many legitimate answers — because RRF scores are
uncalibrated ranks, not relevance.

The golden set is ten question/expected pairs graded by hand on the
deployed page — the only way to tripwire probabilistic behaviour. It
proved itself on first real use: row 3 ("can I take the projector
abroad?") refused live because at top-k=5 the travel chunk was crowded
out of the pool by keyword overlap. Raising top_k to 10 put it at rank
4 and the answer returned, citing the travel rule and the high-demand
priority rule. A unit test could never have caught this; the golden set
did. I graded all ten live: 7/7 answerable — every claim verified
verbatim against the help articles — and 3/3 refusals honest.

Also today: the frontend redesign (bare tables → cards, badges, KPI
rows) — which surfaced two latent bugs, the Geist font silently
overridden by an Arial rule, and a broken dark-mode block. And a small
systems lesson: polling the GitHub API anonymously hit its 60
requests/hour cap — the reason `gh` CLI exists (authenticated requests
get a far higher limit).

One more catch, from reading the live audit log: `request.decide`,
`loan.return` and `loan.extend` recorded only the after-state, so the
Before column was empty even though a prior state existed — the trail
said "it changed" but not what it changed from. Three tests pinned the
behaviour, and each update path now snapshots the entity before
mutating, the same way the asset update paths always did.

**Test yourself:** why can't a score threshold alone decide refusals?
What does top_k control in hybrid retrieval, and what did the golden
set prove about a small pool? Why is the golden set manual rather than
unit-tested?
