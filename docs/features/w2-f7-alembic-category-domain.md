# W2-F7 — Relational Schema Evolution: Alembic Migrations & Category Domain

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` §7 (Day 10)
**Unblocks:** W3-F1 (Quiz Session Creation Backend — sessions table is a new Alembic migration on this schema), W4-F1 (Candidate Results Reporting Endpoints — reporting Alembic env builds on this pattern)
**Last updated:** 2026-06-12

Extend test-management-service's relational models with a "Question Categories"
domain and introduce Alembic for schema migrations.

## Steps

- [ ] **1. Category model** — `Category` SQLAlchemy model in
      test-management-service with `name`, `description`, and M:N relation to
      `Test` via `test_categories` join table.
- [ ] **2. Initialize Alembic** — `alembic init` in test-management-service,
      configure `env.py` to use the service's `DATABASE_URL` and import all
      models for autogenerate.
- [ ] **3. Autogenerate migration** — `alembic revision --autogenerate` to
      produce `0001_add_category.py`; verify up/down.
- [ ] **4. Domain layers** — `CategoryRepository`, `CategoryService`, Pydantic
      schemas (`CategoryCreate`, `CategoryRead`).
- [ ] **5. Gateway routes** — expose CRUD endpoints at
      `/v1/categories` through the API gateway.

## Reporting Service Scaffold (absorbed from W2-M10)

Stand up `reporting-and-analytics-service` at the same time as this feature —
it uses the same Alembic pattern and must exist before W4-F1 can add reporting
tables.

- [ ] **R1. FastAPI scaffold** — `services/reporting-and-analytics-service/main.py`,
      Pydantic settings, `/health` endpoint, `requirements.txt`.
- [ ] **R2. Dedicated datastore** — `reporting-postgres` Postgres container with
      its own named volume in `docker-compose.yml`.
- [ ] **R3. Compose wiring** — reporting service added to `docker-compose.yml`
      with health check and `depends_on: reporting-postgres`.
- [ ] **R4. Alembic init** — `alembic init` in reporting service, `env.py`
      configured for `reporting-postgres`, baseline migration (empty schema).

## Known Defects (surface during verification)

Fix these as they appear when running the stack against the new schema:

- **skill-500** — a specific skill lookup returns 500; trace and patch the
  missing null-guard or ORM join.
- **user-service dual-engine** — user-service initialises two SQLAlchemy
  engines; remove the duplicate and consolidate to one shared engine.
- **Pydantic v2 migration** — any services still using v1-style validators
  (`@validator`, `orm_mode = True`) need updating to v2 (`@field_validator`,
  `model_config`).

## Evidence

None on `tianyac` branch. No Alembic env (`alembic.ini` does not exist in
`services/test-management-service`).

Note: another contributor delivered this feature on branch
`richardh-feat-alembic`; that work is not yet merged into `tianyac`.

## Remaining

All steps. Strict prerequisite for [W3-F1](w3-f1-quiz-session-backend.md) and
[W4-F1](w4-f1-results-reporting-endpoints.md).
