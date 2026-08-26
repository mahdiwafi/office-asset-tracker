# Screenshot capture checklist

Captures of the **live site** (sign-in is Entra-gated, so they are taken by
hand against the deployed app — the local `npm run dev` build looks the same,
but the screenshots should show the real thing).

Save every shot as **PNG**, with exactly the filename listed. Raw size is
fine — the README targets roughly 1200px wide and they are resized before
wiring in. Put the files in this directory (`docs/screenshots/`).

## Shot list

| # | File | Page | What to show |
| --- | --- | --- | --- |
| 1 | `catalog.png` | `/` | The stat cards (Total / Available / On loan / Damaged) and the asset table with status and condition badges |
| 2 | `approvals.png` | `/approvals` | The approval queue with at least one pending request card — the best demo also has one row in **Pending returns** (see prep) |
| 3 | `loans.png` | `/loans` | My loans: an active loan with its **Request return** button; ideally one row with the amber **Return requested** badge (see prep) |
| 4 | `request.png` | `/requests/new` | The raise-request form filled in — justification and a date range, ready to submit |
| 5 | `audit.png` | `/audit` | The trail with one row's **View changes** expander open, showing the before/after JSON |
| 6 | `ask-ict.png` | `/assistant` | A policy question ("How long can I borrow a laptop?") with the grounded answer and its cited sources |

## Prep to make the good shots possible

The approvals and loans screenshots are stronger with a live two-step return
in flight — this is also the flow the demo recording walks through:

1. Log in as staff, raise a request for a loanable asset (with dates), log
   out.
2. Log in as an approver, approve it in `/approvals` — the loan is issued
   automatically.
3. Log back in as staff: `/loans` now shows the active loan. Click
   **Request return** — the row gets the amber badge. Take shot 3 here.
4. Log in as approver: `/approvals` now shows the **Pending returns** table
   with a condition select. Take shot 2 here. (Accept it with *poor* after
   the shot and the catalog shows the asset as damaged + poor — coherent,
   thanks to the return-decision rule.)
5. `/audit` then shows `loan.return_requested` → `loan.return` with the
   before/after snapshots — take shot 5 after the decision.

Shots 1, 4, and 6 need no prep beyond being logged in.

## Capture tips

- **macOS**: `Cmd+Shift+4` drag a region, or `Cmd+Shift+5` for window
  capture. PNG is the default.
- **Full page**: the pages are short enough that a window capture shows
  everything — a region capture of the content area reads best.
- **Date ranges**: pick dates that keep the demo coherent (start today or
  later — the loan-exclusion and 30-day rules are real, and a failed submit
  would show in the shot).
- **Ask ICT**: if the answer renders citations-only (no LLM key in the
  container env yet), that is still a legitimate screenshot — the
  degradation is by design — but the grounded answer with sources is the
  stronger one.
