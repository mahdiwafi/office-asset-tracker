---
name: fastapi-conventions
description: FastAPI structure for this repo — routers per concern, thin handlers, Pydantic schema separation, DI for DB session and current user, consistent error response shape. Prevents inventing a new pattern per endpoint.
---

# FastAPI conventions

## Structure

- `app/api/` — one router module per concern (`health.py`, later `assets.py`, `loans.py`, ...). Routers only: parse request, delegate to service, map to response schema.
- `app/services/` — business rules. All logic that is testable without HTTP lives here. Services receive the DB session as a parameter.
- `app/models/` — SQLAlchemy ORM models, one module per entity.
- `app/schemas/` — Pydantic models. **Three distinct sets, never mixed:**
  - request schemas (what the client sends)
  - response schemas (what the client receives)
  - DB-facing schemas (if needed at all — prefer ORM models internally)
- `app/core/config.py` — settings; no other module reads env vars directly.

## Rules

- **Handlers are thin.** No business logic in a route beyond calling a service and mapping results.
- **Dependency injection for the DB session and current user.** `Depends(get_db)`, later `Depends(get_current_user)` — never instantiate sessions in handlers.
- **Error response shape** — consistent JSON: `{"detail": "..."}` (FastAPI default) or a project-wide error schema; do not mix.
- **Status codes as contract.** 409 for conflicts, 404 for missing, 422 for validation, 401/403 per auth semantics. Defend each in review.
- **Validation at the boundary.** Pydantic validates request/response; services assume validated input.
- **Never expose ORM models in responses.** Convert to response schemas explicitly.

## Schemas

Pydantic v2 style. `model_config = ConfigDict(from_attributes=True)` on response schemas so ORM → schema conversion is explicit and mechanical (`Schema.model_validate(obj)`).
