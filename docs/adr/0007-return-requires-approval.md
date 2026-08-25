# ADR 0007 — Returning a loan requires an approver's decision

## Status

Accepted

## Context

The first version of the return flow let any authenticated user close any
loan with a self-reported condition: `POST /loans/{id}/return` with a
`condition_in` body returned the device, flipped the asset, and wrote the
audit trail in one step. The candidate's review of the flow (a checkpoint
requirement, not a bug report) was explicit: *"return needs approval,
condition is set by the approver."*

Two problems with self-service returns, both real for the product:

- **The borrower grades their own return.** The condition recorded on a
  returned loan is an asset-management decision — *good* returns the asset
  to the pool, *poor* flags it for repair. Allowing the borrower to pick
  the condition lets the returning party decide the repair backlog.
- **Anyone could close anyone's loan.** The endpoint had no ownership or
  role check: any authenticated user could return a device on loan to
  somebody else, unilaterally ending the loan.

The system already has the right machinery for both problems: the
request → decision flow (a requester asks, an approver decides, the
decision is audited) and the `approver`/`admin` role gate.

## Decision

The return flow mirrors the request flow, in two steps:

1. **`POST /loans/{id}/return`** — the borrower (or an approver acting on
   their behalf) marks the loan as pending return. No body: the borrower
   does not record a condition. The loan stays active — the asset remains
   `loaned` and the loan still blocks overlapping dates. The endpoint is
   guarded: the actor must be the loan's borrower or an approver/admin.
   Idempotence is explicit, not silent: a second request, a request on an
   already-returned loan, or a request on a missing loan each raise a
   distinct error (`409`, `409`, `404`).
2. **`POST /loans/{id}/return/decision`** — an approver/admin decides,
   with a `ReturnDecisionBody {decision, condition_in}` mirroring
   `ApprovalDecisionBody` for requests:
   - **approved** requires `condition_in` (a `400` otherwise — the same
     `ReturnConditionMissingError` the old flow used). The loan closes
     (`returned_at`, `condition_in`), the pending marker clears, and the
     asset comes back to the pool — *good*/*fair* → `available`, *poor* →
     `damaged` (flagged for repair). The decision is the inspection: the
     grade also becomes the asset's recorded `condition`, so the catalog
     can never show a *damaged* asset still rated *good*.
   - **declined** cancels the pending request (`return_requested_at`
     cleared) and leaves the loan fully active. The approver grades
     nothing on a decline, so no condition is required.

The pending state is a new nullable column on `loans`,
`return_requested_at` — a column, not a new table, because a pending
return is a property of an existing loan, and the decision only ever
touches that row. The loans list gains a `return_requested=true` filter
(the approvals page's pending-returns view).

Audit actions: `loan.return_requested`, `loan.return`,
`loan.return_declined` — each records `before`/`after` snapshots, so the
trail shows the pending marker appear, and then either the close (with
the condition) or the cancellation.

## Consequences

- **The borrower no longer grades their own return.** The condition
  select moved from My loans to the approval queue, where the approver
  picks it at decision time. My loans shows a single *Request return*
  button and an amber *Return requested* badge while the decision is
  pending.
- **The old contract is gone.** The previous endpoint's `condition_in`
  body shape no longer exists; the frontend and the tests were updated in
  the same change (ADR 0006 did the same for the approval path). There is
  no other consumer.
- **Two new errors join the status map** (both `409`, database-state
  rejections): `ReturnAlreadyRequestedError` and
  `NoReturnRequestedError`. The status-code design comment in
  `app/api/errors.py` holds: identity/role → `403`, payload-only → `400`,
  database state → `409`.
- **A returned loan can be declined.** If the approver decides the device
  is not actually back (or the request is premature), the loan simply
  continues — no state repair needed, because the pending marker was
  never a state change to the loan itself.
- **The rule set is test-pinned.** `tests/test_return_approval.py` names
  each rule — borrower requests, approver-on-behalf, stranger rejected,
  double-request rejected, approve closes, poor → damaged, condition
  required, approver-only decision, decline keeps active, never-requested
  rejected, audit trail — plus HTTP-level tests for the two-step contract
  and the `403` role gate.
