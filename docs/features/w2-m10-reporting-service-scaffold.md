# W2-M10 — Day 10 Milestone: Reporting Service Scaffold

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` milestone §5 (Day 10)
**Related:** W4-F1 (Candidate Results Reporting Endpoints — requires this scaffold + Alembic env)
**Last updated:** 2026-06-12

Stand up the intentionally-empty `reporting-and-analytics-service` following
the same FastAPI + Alembic + Postgres pattern as test-management-service.

## Steps

- [ ] **1. FastAPI scaffold** — `services/reporting-and-analytics-service/main.py`,
      Pydantic settings, health endpoint, `requirements.txt`.
- [ ] **2. Dedicated datastore** — `reporting-postgres` Postgres container with
      its own volume in `docker-compose.yml`.
- [ ] **3. Compose wiring** — reporting service added to `docker-compose.yml`,
      health check, depends_on.
- [ ] **4. Alembic** — `alembic init` in reporting service, `env.py` configured,
      baseline migration (empty schema).
- [ ] **5. Gateway routes** — placeholder `/v1/reporting/**` forwarding rule
      (deferred to W4-F1).

## Evidence

`services/reporting-and-analytics-service/` exists but contains only
`README.md` — a stub from initial brownfield repo setup. No FastAPI app,
no Alembic env, not wired into `docker-compose.yml`.

## Remaining

All steps. Depends on [W2-F7](w2-f7-alembic-category-domain.md) Alembic
pattern being established first.
