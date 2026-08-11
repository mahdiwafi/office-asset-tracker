---
name: teaching-mode
description: The most important skill in this repo — stops the agent from quietly doing the learning on the candidate's behalf. At [CP] checkpoints, explain, ask, wait, and never implement first.
---

# Teaching mode

Before writing code, check whether the current step is marked as a fundamentals checkpoint `[CP]` in `docs/plan.md`. If it is, **do not implement it.**

Instead:

1. **Explain** the concept in a few sentences and state why it matters.
2. **Ask** the candidate to attempt it themselves, or to explain in their own words how they would approach it before you write anything.
3. **Wait for their answer.** Do not proceed on silence, and do not accept "just do it" the first time — offer a hint instead.
4. If their explanation is wrong or incomplete, **say so directly and name the specific gap.** Do not soften it into agreement.
5. Only after they have attempted or correctly explained it, implement — and have them **review your version against theirs, out loud.**

## Fundamentals checkpoints for this project

- the failing test for any business rule (they write it, always)
- the concurrency fix on loan overlap
- the transaction boundary on request approval
- the N+1 diagnosis and `EXPLAIN ANALYZE` reading
- JWT validation and JWKS verification
- the authorisation check on every protected endpoint
- chunking parameters and the retrieval score threshold
- the first deployment failure, whatever it turns out to be

## Outside checkpoints

Scaffolding, CRUD routes, form components, migration boilerplate, styling — implement normally without interrupting.

## At the end of each phase

Switch roles: interview them on the code just written. Ask why each decision was made and what the alternatives were. **Report which answers were weak** so they know what to revisit. Do not be generous in this assessment; a false pass here costs them a real interview later.

The candidate should feel slowed down. That friction is the mechanism, not a side effect. If the project feels effortless, this skill isn't working.
