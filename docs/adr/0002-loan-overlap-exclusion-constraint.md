# ADR 0002 — Enforce the loan-overlap rule with an exclusion constraint

## Status

Accepted

## Context

The business rule — *an asset cannot have two active (not yet returned) loans with overlapping date ranges* — was implemented as a service-layer check: `create_loan` counts active loans overlapping the requested range and raises `LoanOverlapError` if any exist. All 11 sequential rule tests passed.

Under concurrency the check is not sufficient. Two parallel requests were reproduced deterministically: both ran the overlap `SELECT`, both saw zero overlapping loans, both inserted, both committed — `assert 2 == 1`, a double-booking. Under READ COMMITTED isolation a session only sees committed rows, so the second request's check can never see the first request's uncommitted insert. The gap between check and insert is where the guarantee dies.

The invariant can only be enforced where writes are serialized: the database. This is the same philosophy already used for the unique `inventory_tag` — the DB is the final authority, the service translates the DB error.

## Decision

Enforce the rule with a PostgreSQL **exclusion constraint** on `loans`:

```sql
ALTER TABLE loans
  ADD CONSTRAINT loans_no_overlap
  EXCLUDE USING gist (
    asset_id WITH =,
    daterange(start_date, due_date + 1) WITH &&
  )
  WHERE (returned_at IS NULL);
```

- `btree_gist` provides `=` for `asset_id` inside the GiST index.
- `daterange(start_date, due_date + 1)` is half-open `[start, due + 1)`, making the range *inclusive* of the due date — matching the service rule (`start_date <= other.due_date AND due_date >= other.start_date`).
- The partial predicate limits enforcement to active loans, matching the rule exactly.
- An exclusion constraint is an index: a conflicting `INSERT` is rejected by the index itself, atomically with the insert — a conflicting transaction waits for the winner's commit/rollback, then fails. There is no check-then-act gap left to race through.

The service translates the exclusion violation (SQLSTATE `23P01`) into `LoanOverlapError` at flush time in `create_loan` and `extend_loan`. The application-level overlap check is kept as a fast early error for the sequential case; the constraint is the backstop. Candidate chose this over `SELECT ... FOR UPDATE`, on the grounds that the rule lives in the database itself rather than in one code path.

## Consequences

- Requires the `btree_gist` extension (standard contrib — available in the Docker `postgres` image and Azure Database for PostgreSQL). `CREATE EXTENSION` runs inside the migration.
- Slight write overhead on `loans` from index maintenance — negligible at this scale; overlap queries can use the new index.
- The rule now also guards `extend_loan`: moving an active loan's due date into another active loan's range is rejected.
- Changing the rule's semantics (e.g. allowing overlap for different loan kinds) requires a migration.
- Rejected alternative — `SELECT ... FOR UPDATE` on the asset row: a one-line fix, but the guarantee lives in application code (every future code path must remember the lock) and holds a row lock until the caller commits.
