# ADR 0010 — Damaged and maintenance assets cannot be loaned

## Status

Accepted

## Context

The candidate's rule, stated flat: *"damaged and maintenance can't be
loaned."* Two of the three loan paths already enforced something like
it, and one enforced nothing at all:

- **`create_loan`** (direct issuance, API-only) already rejects every
  non-`available` status — `damaged`, `maintenance`, `offboarded`, and
  `loaned` alike (`AssetUnavailableError`).
- **`create_request`** had no asset check at all. Any user could request
  a damaged or maintenance asset, and the approval would then issue the
  loan — the request path let the candidate's rule through in one step.
- **`issue_loan_from_request`** had no availability gate by design
  (ADR 0006): the request may name a period after the current loan
  ends, so the asset can be *loaned* today and free next month. That
  rationale holds for `loaned` — but it also let an asset that turned
  `damaged` (poor return), entered `maintenance`, or was `offboarded`
  after the request was created be issued a loan anyway.

The rule is about *loanability*, not availability: `loaned` stays
requestable (forward reservations are the point of ADR 0006), while the
three statuses that mean "not in service" — `damaged`, `maintenance`,
`offboarded` — must never receive a loan through any path.

## Decision

The loanability gate applies on every path that creates a loan:

1. **`create_request`** rejects a request naming a `damaged`,
   `maintenance`, or `offboarded` asset with `AssetUnavailableError`
   (`409`), before the pending-request and pending-extension checks.
   The request must be possible in principle; the error is the same one
   `create_loan` raises, so the message reads the same everywhere:
   *"asset N is damaged and cannot be loaned."* A `loaned` asset is not
   blocked — the request may book a later window. The asset lookup also
   turns a missing asset into `AssetNotFoundError` (`404`) instead of an
   FK failure, matching `create_loan`'s contract.
2. **`issue_loan_from_request`** re-checks the status at decision time
   and raises the same error. This is the backstop: the asset was fine
   when the request was created, but the world moved — a poor return
   flagged it damaged, staff sent it for repair, or it was retired.
   Because the check runs before any write and `approve_request` never
   commits on failure, the approval fails cleanly and the request stays
   `pending` for the approver to decline.
3. **The request form** only offers `available` and `loaned` assets in
   the picker, defaults the selection to the first requestable row, and
   disables submission with a notice when nothing is requestable — the
   rule is visible before the API enforces it.

This partially supersedes ADR 0006's "no availability gate on the
issuance path": the exception list is exactly the three not-in-service
statuses; the forward-reservation rationale for `loaned` stands.

## Consequences

- **Every loan path enforces the same rule.** Direct issuance
  (`create_loan`), request creation, and approval-side issuance all
  reject the same three statuses with the same error and message.
- **The decision-time backstop changes the approval UX, not the state.**
  Approving a request whose asset turned unloanable returns `409`; the
  request remains pending, the approver declines, and no loan, approval
  row, or audit entry is written.
- **`loaned` is explicitly not blocked.** The forward-reservation tests
  keep passing; the regression guard pins the distinction between
  "unavailable now" (fine — book a later window) and "cannot be loaned"
  (never).
- **The two-way invariant stays intact.** A `damaged` asset is always
  `poor` condition (ADR 0008's check constraint), so seeding and the
  tests must set both together — the new tests mirror the lifecycle
  tests' pattern.
- **The rule is test-pinned at three levels.** Domain tests pin each
  blocked status plus the loaned-allowed case
  (`tests/test_phase1_domain.py`); the issuance backstop lives with the
  other approval-issuance rules (`tests/test_approval_issues_loan.py`);
  and an HTTP test pins the `409` contract on the request endpoint
  (`tests/test_api.py`).
