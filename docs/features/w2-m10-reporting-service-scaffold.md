# W2-M10 — Day 10 Milestone: Reporting Service Scaffold

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` milestone §5 (Day 10)
**Related:** W4-F1 (Candidate Results Reporting Endpoints — requires this scaffold + Alembic env)
**Last updated:** 2026-06-04

Stand up the intentionally-empty `reporting-and-analytics-service` following
the standard service conventions, with its own Postgres datastore under
Alembic control.

## Steps

- [ ] **1. FastAPI scaffold** — `services/reporting-and-analytics-service/`
      currently contains only a README (the seeded empty state). Scaffold the
      standard layout: `main.py` (CORS, `/v1/api` prefix, startup `init_db()`),
      `src/v1/routes/`, `src/services/`, `src/repositories/`, `src/models/`,
      `src/schemas/`, `src/config/settings.py`, `src/db/session.py`,
      `requirements.txt`, `Dockerfile`.
- [ ] **2. Dedicated datastore** — add `reporting-postgres` to
      `docker-compose.yml` (spec topology: 2 Postgres instances; compose
      currently has one, shared by user-service + test-management-service).
- [ ] **3. Compose wiring** — service entry for
      `reporting-and-analytics-service` with healthcheck and
      `condition: service_healthy` dependency on `reporting-postgres`.
- [ ] **4. Alembic** — wire the reporting datastore to Alembic for schema
      history (pattern from [W2-F7](w2-f7-alembic-category-domain.md)).
- [ ] **5. Gateway routes** — once endpoints exist, add patterns to `ROUTES`
      in `services/api-gateway-service/main.py`.

## Remaining

All steps.
