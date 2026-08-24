# Three-minute demo recording — script

The plan's rule: **real usage, not a code tour**. Show the product doing
its job; the interviewer's attention is on the *behaviours* — the
concurrency guarantee, the audit trail, the assistant refusing instead
of inventing.

Length: 3:00. Trim the pre-roll (sign-in is boring; the token check is
not what you are selling). macOS: ⌘⇧5 → record window, capture
microphone.

## Beat sheet

| Time | What is on screen | What you say (in your own words) |
| --- | --- | --- |
| 0:00–0:25 | Sign in (Entra), land on the asset catalog | "Equipment tracking for a small office. One shared source of truth — this is the asset catalog, live, deployed." |
| 0:25–1:05 | Raise a request → open Approvals → approve it | "A request goes to the manager, then ICT. Every decision is written to an append-only audit log — you can scroll it at the end." |
| 1:05–1:30 | My loans: the loan you just approved is there | "The loan shows with its due date. Two people can never hold the same asset on overlapping dates — the database refuses it, not the app." |
| 1:30–2:20 | Ask ICT: "How long can I borrow a laptop?" | "The staff assistant answers from our own policy docs. Every claim cites the exact source — here, the loan-periods article — with the matching score. It is not a black box." |
| 2:20–2:50 | Ask ICT: "What is the capital of France?" | "And when a question is not in our policies, it says so. It refuses instead of inventing — grounded, and honest about its limits." |
| 2:50–3:00 | The repo, CI badge | "Every merge to main builds and deploys. Code, decisions and the build schedule are in the repo." |

## While you are recording (screenshots for the README)

The site is login-gated, so captures are hand-made. Take four PNGs,
~1200px wide, and save them to `docs/screenshots/`:

1. `catalog.png` — the asset catalog
2. `approvals.png` — an approval queue with history
3. `ask-ict-answer.png` — a grounded answer with its cited sources
4. `ask-ict-refusal.png` — the refusal state

Then add them to the README's Screenshots section (the placeholder
marks where). Commit with the usual trailer.

## Before you start

- The deployed frontend auto-updates on push — the Ask ICT page is
  live now, but pull the latest `main` if you want to record from the
  local dev server instead.
- Golden set (docs/golden-set.md): while you are in Ask ICT anyway, run
  the ten questions and fill the Outcome column — that completes the
  Day 7 evaluation row.
- Do not show any token, key, or console output containing them on
  camera.
