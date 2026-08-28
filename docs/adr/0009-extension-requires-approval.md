# ADR 0009 — Extending a loan requires an approver's decision

## Status

Accepted

## Context

The original extension endpoint (`POST /loans/{id}/extend`) moved the due
date immediately — any authenticated user could push their own due date
later with no oversight. The candidate's review of the flow was explicit:
*"loan renewal should just be extend… request extend can be done if
there's no loan request pending, and loan can't be requested if there's a
loan extend pending."* Two requirements in one sentence:

- **Extensions are requests, not actions.** Just like a return, the
  borrower *asks*; the new due date does not move until an approver
  decides. The word "renewal" disappears — there is no renewal state,
  only a request for a later due date.
- **The asset's future is never claimed twice at once.** While a loan
  request is pending on an asset, an extension request on its active loan
  is blocked; while an extension request is pending, new loan requests
  on that asset are blocked. Either way the approver decides the asset's
  next window first.

ADR 0007 established the pattern this builds on: a pending marker on the
loan row plus a paired decision endpoint, with the approver/admin role
gate at decision time.

## Decision

The extension flow mirrors the return flow in two steps:

1. **`POST /loans/{id}/extend`** with `{new_due_date}` — the borrower (or
   an approver acting on their behalf) marks the loan as pending
   extension. `extend_requested_at` and `extend_due_date` are set; the
   loan's `due_date` does not move. Guard chain, in order:
   - loan exists (`404`), not returned (`409`), no pending return
     (`409`), no pending extension (`409`),
   - the requested date must be *later* than the current due date —
     equal or earlier is rejected as `InvalidExtensionError` (`409`),
   - **Rule A (candidate's first exclusion):** a pending loan request on
     the asset blocks the extension (`PendingRequestExistsError`,
     `409`),
   - the overdue escalation guard survives from the old flow: an
     extension of an overdue loan still requires its original request to
     carry an approved approval (`OverdueExtensionError`, `409`),
   - the actor must be the loan's borrower or an approver/admin
     (`NotAnApproverError`, `403`).
2. **`POST /loans/{id}/extend/decision`** with
   `{decision: 'approved' | 'declined'}` — an approver/admin decides:
   - **approved** clears the pending markers and writes
     `due_date = extend_due_date`. The write is protected by the same
     exclusion constraint as every other date move: if the extension
     would overlap another active loan, the database rejects it
     (`23P01` → `LoanOverlapError`, `409`) — the race between request and
     decision cannot slip past the DB.
   - **declined** clears both markers and leaves the loan exactly as it
     was. The due date never moved, so no state repair is needed.

And **Rule B (the second exclusion, in `create_request`)**: a loan
request is rejected while the asset has an active loan with a pending
extension request (`PendingRequestExistsError`, `409`). Both rules
re-use the existing error so both rejections read the same on the
request form.

The pending state is two nullable columns on `loans`,
`extend_requested_at` and `extend_due_date` — columns, not a new table,
for the same reason as ADR 0007: a pending extension is a property of an
existing loan, and the decision only ever touches that row. The loans
list gains an `extend_requested=true` filter (the approvals page's
pending-extensions view).

Audit actions: `loan.extend_requested`, `loan.extend`,
`loan.extend_declined` — each records `before`/`after` snapshots, so the
trail shows the request appear, then either the due-date move or the
cancellation.

## Consequences

- **The borrower no longer moves their own due date.** My loans shows an
  *Extend* button that opens a date picker (defaulting to one week past
  the due date, min = due date) and an amber *Extension pending* badge
  while the decision is out. The approvals page gains a *Pending
  extensions* section next to pending returns.
- **The old contract is gone.** The previous endpoint moved the date in
  one step; the new one only requests. There is no other consumer, so
  the frontend and tests were updated in the same change.
- **The two-way exclusion is test-pinned in both directions.** A pending
  loan request blocks the extension; a pending extension blocks new loan
  requests — at the domain level (`tests/test_phase1_domain.py`) and
  over HTTP (`tests/test_api.py`), each asserting its own message.
- **Three new errors join the status map** (all `409`, database-state
  rejections): `ExtendAlreadyRequestedError`,
  `NoExtendRequestedError`, `InvalidExtensionError`. The status-code
  design comment in `app/api/errors.py` holds: identity/role → `403`,
  payload-only → `400`, database state → `409`.
- **A declined extension leaves no trace on the loan.** Because the due
  date never moved, cancelling the request restores the loan exactly —
  the decline path is pure marker clearing.
- **The rule set is test-pinned.** `tests/test_extend_approval.py` names
  each rule — borrower requests, approver-on-behalf, stranger rejected,
  returned loan rejected, double-request rejected, blocked while a
  return is pending, equal/earlier dates rejected, extension blocked
  while a loan request is pending, approve moves the date, approve into
  an overlapping loan rejected, approver-only decision, decline keeps
  the loan unchanged, never-requested rejected — plus HTTP-level tests
  for the two-step contract and the `403` role gate.
