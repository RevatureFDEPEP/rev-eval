# W2-F7 — Relational Schema Evolution: Alembic Migrations & Category Domain

**Status:** ✅ Completed
**Spec:** `docs/feature_specs/w2-f7-alembic-category-domain.md`
**Plan:** `docs/plans/w2-f7-alembic-category-domain-plan.md`
**Unblocks:** W3-F1 (Quiz Session Creation Backend), W4-F1 (Candidate Results Reporting Endpoints)
**Branch:** `tianyac-alembic-migrations`
**Last updated:** 2026-06-17

---

## Steps

- [x] **1. Category model** — `Category` SQLAlchemy model in test-management-service with `name`,
      `description`, and M:N relation to `Skill` via `skill_categories` join table (`Table` object,
      composite PK on `category_id` + `skill_id`). *(Initial impl used `test_categories` M2M with
      `Test`; corrected to `skill_categories` M2M with `Skill` per spec in commit `fb441bc`.)*
- [x] **2. Alembic migrations** — `0005_add_categories.py` (`down_revision="0004"`) creates
      `categories` + `test_categories`; `0006_replace_test_categories_with_skill_categories.py`
      (`down_revision="0005"`) drops `test_categories`, creates `skill_categories`. Head is `0006`
      after W2-F7; W3-F2 adds `0007`.
- [x] **3. Domain layers** — `CategoryRepository` (async CRUD), `CategoryService` (raises
      `ValueError` on not-found), Pydantic schemas `CategoryCreate`, `CategoryUpdate`, `CategoryOut`
      (Pydantic v2 `ConfigDict(from_attributes=True)`).
- [x] **4. Gateway routes** — CRUD endpoints at `/v1/api/categories` through API gateway;
      pattern `^/v1/api/categories(/.*)?$` → test-management-service added to gateway `ROUTES`.
      Also `POST/DELETE /v1/api/categories/{id}/skills/{skill_id}` link/unlink endpoints
      (added in `fb441bc`).

## Reporting Service Scaffold (absorbed from W2-M10)

- [x] **R1. FastAPI scaffold** — `services/reporting-and-analytics-service/main.py`,
      `src/config/settings.py` (Pydantic BaseSettings, port 8004), `/health` endpoint,
      `requirements.txt`.
- [x] **R2. Dedicated datastore** — `reporting-postgres` Postgres 15 container with named
      volume `reporting_postgres_data` in `docker-compose.yml`.
- [x] **R3. Compose wiring** — reporting service added to `docker-compose.yml` with health check
      (`curl /health`) and `depends_on: reporting-postgres: condition: service_healthy`.
- [x] **R4. Alembic init** — `alembic.ini`, `migrations/env.py` (sync psycopg2 engine),
      `migrations/script.py.mako`, baseline migration `0001_baseline.py` (no-op, `down_revision=None`).

## Known Defects — Fixed

- [x] **skill-500** — `SkillService.get_skill_by_id` method was missing; route called it →
      `AttributeError` → 500. Added method to `src/services/skill_service.py`.
- [x] **user-service dual-engine** — `session.py` created its own `engine`/`SessionLocal` while
      also importing `Base` from `init_db.py`. Fixed: `session.py` now imports all three
      (`Base`, `SessionLocal`, `engine`) from `init_db.py`.
- [x] **Pydantic v2 migration** — audited all services; no `@validator` or `orm_mode = True`
      found. No changes required.

## Evidence

**Branch:** `tianyac-alembic-migrations`
**Commits:** `117f333` (initial impl), `65806a1` (ruff fixes), `fb441bc` (Skill M2M correction + migration 0006 + link/unlink endpoints)

Files created:

| File | Purpose |
|---|---|
| `services/test-management-service/src/models/category.py` | `Category` model + `skill_categories` Table |
| `services/test-management-service/src/schemas/category_schema.py` | Pydantic v2 schemas |
| `services/test-management-service/src/repositories/category_repository.py` | Async CRUD + link/unlink |
| `services/test-management-service/src/services/category_service.py` | Business logic layer + link/unlink |
| `services/test-management-service/src/v1/routes/category_route.py` | 5 CRUD + 2 link/unlink endpoints |
| `services/test-management-service/migrations/versions/0005_add_categories.py` | Creates `categories` + `test_categories` |
| `services/test-management-service/migrations/versions/0006_replace_test_categories_with_skill_categories.py` | Drops `test_categories`, creates `skill_categories` |
| `services/reporting-and-analytics-service/main.py` | FastAPI scaffold |
| `services/reporting-and-analytics-service/requirements.txt` | Dependencies |
| `services/reporting-and-analytics-service/Dockerfile` | Container definition |
| `services/reporting-and-analytics-service/src/config/settings.py` | Pydantic settings |
| `services/reporting-and-analytics-service/alembic.ini` | Alembic config |
| `services/reporting-and-analytics-service/migrations/env.py` | Sync migration runner |
| `services/reporting-and-analytics-service/migrations/script.py.mako` | Migration template |
| `services/reporting-and-analytics-service/migrations/versions/0001_baseline.py` | Empty baseline |

Files modified:

| File | Change |
|---|---|
| `services/test-management-service/src/models/test.py` | Added (then removed) `categories` relationship |
| `services/test-management-service/src/models/skill.py` | Added `categories` back-reference |
| `services/test-management-service/migrations/env.py` | Added `src.models.category` import |
| `services/test-management-service/src/db/session.py` | Import `category` in `init_db()` |
| `services/test-management-service/main.py` | Registered `category_router` |
| `services/test-management-service/tests/conftest.py` | Import `Category` for mapper resolution |
| `services/test-management-service/src/services/skill_service.py` | Added `get_skill_by_id` |
| `services/user-service/src/db/session.py` | Removed duplicate engine; imports from `init_db` |
| `services/api-gateway-service/main.py` | Added `/v1/api/categories` route pattern |
| `docker-compose.yml` | Added `reporting-postgres` + `reporting-and-analytics-service` |

**Test result:** 133 passed, 0 failed (`pytest tests/ -q` in test-management-service).

## Remaining

None. All acceptance criteria met.
