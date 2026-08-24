# Assistant golden set

Ten question/expected pairs for the RAG assistant, sampled across the
families it actually meets: exact, paraphrase, fuzzy, eligibility, and
the three refusal mechanics (below-floor deterministic, model referee
for semantic mismatch, noise). The six help articles all appear as an
expected source; the refusal rows expect no article at all.

Why this exists is the point of ADR 0005: retrieval and generation are
probabilistic, the hermetic suite proves wiring, and this set is the
manual tripwire for quality.

## Running it

    uv run python -m scripts.golden_set

with `AI_SEARCH_ENDPOINT`/`AI_SEARCH_KEY` set. The answer and refusal
columns additionally need `LLM_API_KEY` — the deployed container has
one, so running the same ten questions on the **Ask ICT** page grades
the full stack; the script is the same service, one step closer.

## Rubric

- **Retrieval** — does the expected article appear in the top-5
  citations? (For refusal rows, noise is expected and harmless.)
- **Outcome** — for answerable pairs: does the answer state the policy
  fact from the cited article and nothing else? For refusal rows: does
  the assistant say it cannot answer instead of inventing one?

## The set

Retrieval column from the live run of 2026-08-24 (generation OFF — no
local key). Outcome column is graded by hand on the deployed Ask ICT
page, which runs with the key.

| # | Family | Question | Expected article | Retrieval (top-5) | Outcome |
| --- | --- | --- | --- | --- | --- |
| 1 | exact | How long can I borrow a laptop? | loan-periods | ✅ rank 2 (eligibility-and-priority noise on top) | |
| 2 | exact | What do I return when I leave the company? | offboarding-returns | ✅ rank 1 | |
| 3 | paraphrase | I am flying abroad for a client workshop — can I take the projector with me? | asset-care | ✅ rank 5 (eligibility-and-priority on top) | |
| 4 | paraphrase | How do I get a second monitor for report writing? | requesting-equipment | ✅ rank 1 | |
| 5 | fuzzy | My laptop screen is cracked, what should I do? | damage-and-loss | ✅ rank 1 | |
| 6 | paraphrase | Can I keep a headset for the whole project? | loan-periods | ✅ rank 3 (asset-care on top) | |
| 7 | eligibility | Who gets a camera when several people want one? | eligibility-and-priority | ✅ rank 1 | |
| 8 | near-miss | What time does the office open? | — (noise fine) | noise: damage-and-loss — must refuse | |
| 9 | out-of-scope | What is the capital of France? | — (noise fine) | noise: asset-care — must refuse | |
| 10 | nonsense | zzzzqqqq | — (noise fine) | noise: damage-and-loss — floor refusal, no model call | |

Reading the scores: everything landed in 0.0299–0.0333 regardless of
relevance — the same uncalibrated RRF band as the refusal battery. The
top-1 vs rank-5 gaps (0.0003–0.0027) are meaningless; what matters is
whether the expected article is in the top-5 at all, and whether the
model picks the right excerpt when several candidates are near-equal.

## Reference facts (for grading)

1. **Loan periods** — standard period is 14 days; the due date in the
   tracker is the binding one. Renewals: twice, +14 days each, only if
   nobody is waiting; long-term needs go through a request with
   "long-term" in the notes, not endless renewals.
2. **Returning** — laptop and charger, phone and SIM, dongles/adapters/
   headsets/keyboards/mice, project equipment, permanently assigned
   items; hand back in person or by tracked mail that reaches the
   office; personal files backed up, office files not copied.
3. **Travel** — borrowed equipment may go on business travel including
   abroad without special permission; same 24-hour damage/loss rule.
4. **Requesting** — raise a request (manager, then ICT), most decided
   within two working days; check the asset list first — shared items
   may be borrowable immediately.
5. **Damage** — report within 24 hours via the tracker; small accidents
   (cracked screen, spilled coffee) are covered; never repair outside
   ICT; negligence (repeated, deliberate, under influence, unattended
   in public) is charged.
6. **Long-term needs** — do not keep renewing; raise a request with
   "long-term" in the notes for a formal assignment.
7. **Priority** — high-demand items (high-spec laptops, phones, cameras,
   projectors): operational need, external commitments, accessibility,
   then request order as tie-breaker.
8–10. **Refusal** — the assistant must say it cannot answer (near-miss
   and out-of-scope via the model referee; nonsense hits the 0.020 floor
   and refuses deterministically without a model call).
