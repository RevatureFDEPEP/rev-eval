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

## Evidence

None on `tianyac` branch. No Alembic env (`alembic.ini` does not exist in
`services/test-management-service`).

Note: another contributor delivered this feature on branch
`richardh-feat-alembic`; that work is not yet merged into `tianyac`.

## Remaining

All steps. Strict prerequisite for [W3-F1](w3-f1-quiz-session-backend.md) and
[W4-F1](w4-f1-results-reporting-endpoints.md).
