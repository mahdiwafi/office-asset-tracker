# ADR 0005 — Evaluating the assistant with a manual golden set

## Status

Accepted

## Context

The assistant is probabilistic end-to-end: embeddings, RRF merging and
the generative model all sit behind provider fakes in the test suite.
The hermetic tests prove wiring — the request shape, the citation
logic, the refusal-floor decision — and cannot prove that a question
gets a good answer, because a good answer depends on the real index
and the real model. Every quality decision so far was made against
live data for exactly this reason: the refusal floor of 0.020 (ADR 0004
family, Day 7) came from a 16-query live score battery (2026-08-24)
which also showed RRF scores are rank-based and uncalibrated — every
real-word query, including out-of-scope ones, landed in 0.0315–0.0333
while pure nonsense scored 0.0167. Unit-testing such a system is
provably dead; the question is what replaces it.

## Decision

Maintain a **golden set of ten question/expected pairs** in
`docs/golden-set.md`, sampled across the families the assistant meets —
exact, paraphrase, fuzzy, eligibility, near-miss, out-of-scope,
nonsense — covering all six help articles plus the three refusal
mechanics (below-floor deterministic, model referee for semantic
mismatch, no-key citations-only). `scripts/golden_set.py` runs the set
against the live services and prints a transcript; **grading is manual**
(retrieval: expected article in top-5? outcome: does the answer state
the policy fact, or refuse when it should?). Run it whenever the corpus,
the index, or the retrieval/generation stack changes, and record results
in the table.

## Consequences

- The golden set is the tripwire a probabilistic system can have: no
  regression safety, but a fast, honest signal that a corpus edit or
  provider swap quietly degraded answers.
- It only fires when someone runs it — schedule it into the ingest
  workflow, not just the build.
- It doubles as demo material and as manual-evaluation evidence for the
  interview, and it does not replace the hermetic suite: wiring tests
  and manual evaluation test different claims, and both are kept.
