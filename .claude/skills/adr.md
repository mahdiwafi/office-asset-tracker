---
name: adr
description: Architectural Decision Records in Michael Nygard format — context, decision, status, consequences. Trigger on any architectural choice, no matter how small it seems.
---

# ADR — Architectural Decision Records

Format (Michael Nygard), one file per decision in `docs/adr/`:

```markdown
# ADR NNNN — Title

## Status
Accepted | Proposed | Superseded by ADR NNNN

## Context
The forces at play, the constraint, the thing that makes this a decision
rather than a default. Facts and problem framing only — no solution yet.

## Decision
What we decided to do, stated directly.

## Consequences
What this enables, what it costs, what it makes harder later.
```

**Trigger on any architectural choice** — stack components, concurrency control, schema decisions, auth model, retrieval strategy. A history of small, honest ADRs is the difference between a portfolio project and a portfolio project that demonstrates seniority.

Number sequentially (`0001-...`). Never rewrite history — supersede instead. Write the ADR the moment the decision is made, not at the end of the phase.
