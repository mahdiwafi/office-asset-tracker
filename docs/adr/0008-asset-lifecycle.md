# ADR 0008 — The asset lifecycle is a state machine

## Status

Accepted

## Context

The first version of the status endpoint (`PATCH /assets/{id}/status`)
was a free-form write: any authenticated user could set any status on
any asset. Three problems followed, one of them observed on the live
catalog:

- **A poor-condition asset sat in the pool.** The catalog showed an
  asset *available* while its condition was *poor* — and a *damaged*
  asset still rated *good* (fixed in ADR 0007's return flow). Nothing
  linked the condition grade to where the asset may live.
- **Staff had no maintenance action in the UI**, even though the
  endpoint existed — the statuses were rendered but never changeable
  from the product.
- **Anyone could offboard anything**, including assets currently on
  loan, with no role gate and no audit rules.

The product rule, stated by the candidate: *"poor is always damaged
and can be maintenanced"* — a poor asset is out of the pool, either
damaged awaiting repair or already in maintenance, and any staff
member can move an item into maintenance.

## Decision

The status endpoint becomes a small state machine, and the invariant
is enforced at every layer:

1. **The invariant: `condition = poor` ⇒ `status ∈ {damaged,
   maintenance}`.** A poor asset can never be `available` or `loaned`.
   - *Database:* a CHECK constraint (`ck_assets_poor_condition_status`)
     makes the invariant structural — even a direct write outside the
     app cannot put a poor asset in the pool (same philosophy as the
     loans exclusion constraint, ADR 0002).
   - *Create:* an asset created with `condition = poor` must start
     `damaged` or `maintenance` (`AssetPoorConditionError`, `409`).
2. **The transitions.** The endpoint accepts three targets and nothing
   else:
   - `maintenance` — any staff member, never while the asset is on
     loan (`AssetOnLoanError`, `409`). Condition is not re-graded; a
     poor dock stays poor in maintenance.
   - `available` — **only from `maintenance`**, and the repair resets
     the recorded condition to `good` (`InvalidAssetStatusTransitionError`,
     `409` otherwise). The pool is reached through the repair queue,
     and a repaired asset is graded good — never poor.
   - `offboarded` — approver/admin only (`NotAnApproverError`, `403`),
     never while on loan (`AssetOnLoanError`, `409`), and terminal: an
     offboarded asset cannot change status again.
   - `loaned` and `damaged` are not settable here at all: loaning is
     the loan flow's job (availability gate, overlap exclusion) and
     damage is recorded by the return decision, the inspection
     (ADR 0007). `InvalidAssetStatusTransitionError`, `409`.
   - Setting the current status is a no-op: no state change, so no
     audit event.
3. **The UI.** The asset detail page gains lifecycle actions: *Send to
   maintenance* for staff (disabled on loaned assets), *Repair (back
   to available)* and *Offboard* for approvers, nothing on offboarded
   assets. Every action goes through the same audited endpoint
   (`asset.status_change`, before/after snapshots).

The full cycle, end to end: a poor return puts the asset in
`damaged` → staff sends it to `maintenance` → the repair returns it
`available` with condition `good`. Every step is audited.

## Consequences

- **The catalog can no longer contradict itself.** Status and
  condition are coherent by construction: `available` implies
  `condition ≠ poor`, and the only ways out of the pool are the
  return decision and the repair queue.
- **The blunt writes are gone.** Directly marking an asset `loaned` or
  `damaged` via the endpoint now fails with a clear `409` instead of
  silently bypassing the flows that own those states.
- **Four new errors join the status map** (all `409`, database-state
  rejections): `AssetOnLoanError`, `AssetPoorConditionError`,
  `InvalidAssetStatusTransitionError`, plus `NotAnApproverError`
  (`403`) for offboarding. The design comment in `app/api/errors.py`
  still holds.
- **Offboarding is now a gated, terminal action.** It is approver-only
  and irreversible through the app — an asset leaves the pool for
  good, and the audit trail records who did it and from what state.
- **The rule set is test-pinned.** `tests/test_asset_lifecycle.py`
  names every rule at the service layer (staff maintenance, loaned
  guard, approver-only offboard, terminal offboard, repair-only
  return-to-pool, repair resets condition, poor-create rejection,
  no-op not audited, missing asset), HTTP-level tests cover the
  contract and the `403`/`409`s, and one test proves the CHECK
  constraint rejects a poor `available` asset at the database layer.
