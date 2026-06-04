# F7 — Relational Schema Evolution: Alembic Migrations & Category Domain

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` §7 (Day 10)
**Unblocks:** W3-F1 (Quiz Session Creation Backend — sessions table is a new Alembic migration on this schema), W4-F1 (Candidate Results Reporting Endpoints — reporting Alembic env builds on this pattern)
**Last updated:** 2026-06-04

Extend test-management-service's relational models with a "Question Categories"
domain and bring schema changes under Alembic migration control.

## Steps

- [ ] **1. Category model** — new SQLAlchemy model `Category` (topics like
      "Python", "Docker", "Algorithms") in
      `services/test-management-service/src/models/`, with a many-to-many
      relationship to `Skill` (association table).
- [ ] **2. Initialize Alembic** — no `alembic/` or `alembic.ini` exists in any
      service. Init inside `services/test-management-service/`, wire `env.py`
      to the async SQLAlchemy metadata and env-driven DB URL
      (`src/config/settings.py`).
- [ ] **3. Autogenerate migration** — `alembic revision --autogenerate -m "Add
      categories and skills relationship"`, review the script, `alembic upgrade
      head`.
- [ ] **4. Domain layers** — repository, service, and router layers for
      fetching, creating, and linking Categories, following the standard layout
      (`src/repositories/` → `src/services/` → `src/v1/routes/`).
- [ ] **5. Gateway routes** — add new endpoint patterns to `ROUTES` in
      `services/api-gateway-service/main.py`.

## Notes

- Tables are currently created on startup via `init_db()` — once Alembic owns
  the schema, decide whether `init_db()` keeps `create_all` for dev or defers
  to migrations.
- The reporting service ([M10](m10-reporting-service-scaffold.md)) reuses the
  Alembic pattern established here.

## Remaining

All steps.
