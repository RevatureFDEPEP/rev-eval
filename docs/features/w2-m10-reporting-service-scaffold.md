# W2-M10 — Day 10 Milestone: Reporting Service Scaffold

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` milestone §5 (Day 10)
**Related:** W4-F1 (Candidate Results Reporting Endpoints — requires this scaffold + Alembic env)
**Last updated:** 2026-06-09

Stand up the intentionally-empty `reporting-and-analytics-service` following
the standard service conventions, with its own Postgres datastore under
Alembic control.

## Steps

- [x] **1. FastAPI scaffold** — standard layout under
      `services/reporting-and-analytics-service/`: `main.py` (CORS, `/v1/api`
      router prefix, startup `init_db()`, `/health`), `src/config/settings.py`,
      async `src/db/session.py`, empty `src/{v1/routes,services,repositories,
      models,schemas}/`, `requirements.txt`, `requirements-dev.txt`,
      multi-stage `Dockerfile` (base→test→production, Trivy base-image tooling
      upgrade), `pytest.ini`, `conftest.py`, `.coveragerc`, smoke tests. Port
      **8004** (`cc78671`).
- [x] **2. Dedicated datastore** — `reporting-postgres` added to
      `docker-compose.yml` (2nd Postgres instance; own volume
      `reporting_postgres_data`, host port **5433**, DB `eval_ai_reporting`),
      `REPORTING_POSTGRES_*` in `.env.example` (`cdbed80`).
- [x] **3. Compose wiring** — `reporting-and-analytics-service` entry on 8004,
      `/health` healthcheck, `depends_on: reporting-postgres:
      condition: service_healthy` (`323cc96`).
- [x] **4. Alembic** — async env mirroring test-management-service (runtime
      asyncpg URL, `compare_type`, owned-tables `include_object` filter), empty
      `0001` baseline, `start.sh` (wait → `alembic upgrade head` → run); no
      legacy stamp branch (fresh datastore). Pattern from
      [W2-F7](w2-f7-alembic-category-domain.md) (`45e2f50`).
- [~] **5. Gateway routes** — **N/A at this milestone, deferred to W4-F1.** The
      scaffold exposes only `/health` (compose healthcheck, not gateway-routed);
      there are no business endpoints yet. The detail wording is "once endpoints
      exist" — W4-F1 adds the `/v1/api/reports…` pattern to `ROUTES` in
      `services/api-gateway-service/main.py` when those endpoints land.

## Beyond the listed steps

- **CI matrix parity** — `reporting-and-analytics-service` added to the
  `ci-pipeline.yml` backend matrix (path filter + `all` job set) so it gets
  Ruff / Trivy / coverage gates like the other four backends (`e935f64`).

## Evidence

- Branch `richardh-feat-W2M10`; plan
  [`docs/plans/w2-m10-reporting-service-scaffold.md`](../plans/w2-m10-reporting-service-scaffold.md).
- Fresh `docker compose up --build postgres reporting-postgres
  reporting-and-analytics-service`: all three healthy; logs show
  `alembic upgrade head` running `-> 0001`; `eval_ai_reporting.alembic_version`
  = `0001`; `:8004/health` → `{"status":"ok"}`; shared `postgres`/`eval_ai_dev`
  untouched (no 5432/5433 clash).
- `pytest --cov` green (78%, `.coveragerc fail_under=75`); `ruff check` clean;
  `docker build --target test` passes the in-image pytest gate.
- Alembic offline `upgrade head --sql` creates `alembic_version` + stamps
  `0001`; `alembic history` shows `<base> -> 0001 (head)`.

## Remaining

Steps 1–4 done. Step 5 (gateway routes) intentionally deferred to W4-F1 — no
endpoints to route yet.
