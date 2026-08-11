---
name: db-migrations
description: Alembic workflow — never edit an applied migration, always review autogenerate output before committing, one migration per logical change.
---

# DB migrations

- **Never edit an applied migration.** Applied = present in the migration history (`alembic_version`). Fix forward with a new migration.
- **Always review autogenerate output before committing.** Autogenerate misses some things (constraint renames, some indexes) and guesses others. Read the diff.
- **One migration per logical change.** Squash review noise; keep history legible.
- Workflow:
  1. `uv run alembic revision --autogenerate -m "short description"`
  2. Read the generated file carefully against the models.
  3. `uv run alembic upgrade head`
  4. Verify with a quick query or a test against the schema.
- Downgrade paths must work (`alembic downgrade -1`) — no destructive irreversible steps in early migrations unless explicitly approved.
- In CI: migrations run as part of tests or deploy, never skipped.
