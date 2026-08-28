# ADR 0006 — Approving a request with dates issues the loan

## Status

Accepted

## Context

The product flow promised a closed loop — *raise a request, an approver approves it, the loan appears in My loans* — but nothing implemented the last step. `approve_request` wrote four rows (the `Approval` row, `request.status`, `request.decided_at`, the audit entry) and stopped: loans were only created through the `create_loan` API endpoint, which no UI calls, and the unique `Loan.request_id` foreign key sat unused for exactly this purpose. The live consequence, found by the candidate during recording prep: "my loans empty, available don't get changed into loaned, loaned asset can be requested and approved." An approved asset stayed available, so it could be requested and approved again — twice-consented, twice-decided, with no loan anywhere.

The recording script is the contract for this system, and its beat at 0:25–1:05 ("Raise a request → approve it → the loan is in My loans") cannot be narrated from the approved state alone.

## Decision

An approved request that names an asset **and** a date range issues the loan inside the decision's transaction. `approve_request` calls `issue_loan_from_request` before writing the `request.decide` audit record; the loan is built from the request (borrower = requester, `condition_out` good, dates as requested) and inserted through the same `_finalize_loan` helper that `create_loan` uses — the `23P01` exclusion-constraint translation, the asset status flip to `loaned`, and the `loan.create` audit entry are one code path, not two.

Three properties of this design are deliberate:

- **No availability gate on the issuance path.** The request may name a period after the current loan ends — the asset can be loaned *today* and free *next month*. The exclusion constraint (ADR 0002) is the guarantee that matters: it rejects only actual date overlap. This is why approval can issue a loan for a currently-unavailable asset while `create_loan` still requires availability: the API path books out of the pool, the approval path books the requested period.
- **Requests without dates stay consent-only.** The two approved requests in the live database have no dates; approving them must not conjure loans. `issue_loan_from_request` returns `None` when the asset or either date is missing.
- **The loan is atomic with the decision.** The service never commits; the router owns the transaction (Day 2's boundary). If the caller dies after the decision, the loan and its audit entry vanish with it — no orphaned loan for a decision that never happened.

The frontend request form carries the two dates (start today, due +14 by default, capped at 30 days — the same maximum `create_loan` enforces), so the UI flow always produces a loan on approval.

## Consequences

- The asset status flip is now part of loan creation: a loaned asset fails `create_loan`'s availability gate before the overlap check. The sequential double-booking test asserts the new message; the concurrency race test accepts either rejection — which one surfaces depends on when the loser's asset read lands, and both prove the same invariant, exactly one loan.
- `return_loan` now closes the loop on the asset: a good-condition return restores `available`, a poor-condition return leaves the asset `damaged` for repair.
- Consent-only requests remain possible (API-only issuance) but the UI always submits dates; the 30-day cap is validated on both sides, client and service.
- Two paths now write loans; the `_finalize_loan` helper keeps them from drifting apart — a future third path (e.g. bulk transfer) should route through it too.
- **Superseded in part by ADR 0010.** The "no availability gate on the issuance path" clause gains one exception: `damaged`, `maintenance`, and `offboarded` assets are never issued a loan, at request time or at decision time. The forward-reservation rationale for `loaned` assets stands.
