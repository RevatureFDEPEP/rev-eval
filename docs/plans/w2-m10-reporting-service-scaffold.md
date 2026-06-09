# W2-M10 — Reporting Service Scaffold (plan)

**Feature:** W2-M10 — Day 10 Milestone: Reporting Service Scaffold
**Detail doc:** [`docs/features/w2-m10-reporting-service-scaffold.md`](../features/w2-m10-reporting-service-scaffold.md)
**Spec:** `days_6_10_features.md` milestone §5 (Day 10) — "Scaffolded Reporting microservice"
**Depends on:** [W2-F7](../features/w2-f7-alembic-category-domain.md) (Alembic pattern — ✅ done)
**Unblocks:** W4-F1 (Candidate Results Reporting Endpoints — needs this scaffold + initialized Alembic env)

**Locked user decisions:**
1. **Empty `0001` baseline** — wire `env.py` to `Base.metadata` (no models yet) and
   author one empty `0001` baseline revision so `alembic upgrade head` runs and
   creates `alembic_version` at this milestone. W4-F1 autogenerates `0002+` onto it.
2. **Add the new service to the CI matrix** — path filter + `all` list entry in
   `ci-pipeline.yml` so reporting gets Ruff / Trivy / coverage parity with the
   other four backends.

## Context

`services/reporting-and-analytics-service/` is empty by design — only a 0-byte
`README.md` (seeded placeholder). The spec topology calls for **2 Postgres
instances**; compose currently has **one** (`postgres`, shared by user-service +
test-management-service). This milestone stands the service up on the standard
FastAPI layout with its **own** `reporting-postgres` datastore under Alembic.

Key conventions to match (from the existing 4 services):
- Layout: `main.py` (CORS, `/v1/api` router prefix, startup `init_db()`, `/health`),
  `src/{config,db,v1/routes,services,repositories,models,schemas}/`,
  `requirements.txt`, `requirements-dev.txt`, `Dockerfile` (multi-stage
  base→test→production), `pytest.ini`, `conftest.py`, `.coveragerc`.
- **Async SQLAlchemy** (`asyncpg`) like test-management-service; `settings.py`
  via `pydantic-settings` (DB_HOST/PORT/USERNAME/PASSWORD/NAME).
- **Alembic** mirrors test-management-service exactly: `alembic.ini` with blank
  `sqlalchemy.url`, `alembic/env.py` async, URL resolved at runtime from
  `DATABASE_URL`/settings forcing `postgresql+asyncpg://`, `compare_type=True`,
  `include_object` filter (its DB is private — filter is defensive parity, not
  load-bearing here since nothing else shares `eval_ai_reporting`).
- **Startup**: `start.sh` waits for Postgres, `alembic upgrade head` (fail-hard),
  then `exec python main.py`. No legacy `alembic stamp` adopt branch needed —
  this is a brand-new datastore (fresh volume always).
- Dockerfile upgrades base-image tooling (pip/setuptools/wheel/jaraco.context)
  before `pip install` — required to pass the Trivy CRITICAL/HIGH gate (W2-F4).
- Port: **8004** (next free; table currently lists `—`). Host Postgres port
  **5433** to avoid clashing with the shared `postgres` on 5432.

**Step 5 (gateway ROUTES) is N/A at this milestone.** The detail doc says "once
endpoints exist." The scaffold exposes only `/health` (compose healthcheck, not
gateway-routed). No business endpoints → no `ROUTES` pattern yet; W4-F1 adds the
`/v1/api/reports…` pattern when those endpoints land. Documented, not skipped.

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W2M10`** off `richardh` before any change.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — FastAPI scaffold (detail step 1)
Create `services/reporting-and-analytics-service/`:
- `main.py` — `FastAPI(title="Reporting and Analytics Service")`, CORS from
  `settings.ALLOW_ORIGINS`, `/health` returning `{"status": "ok"}`, startup
  `on_startup()` calling `init_db()`. Router includes with `prefix="/v1/api"`
  are scaffolded but empty (no routes yet — comment pointing to W4-F1).
- `src/config/settings.py` — `Settings(BaseSettings)`: `DB_HOST/PORT/USERNAME/
  PASSWORD/NAME`, `ALLOW_ORIGINS="*"`, `SERVICE_NAME="reporting-and-analytics-service"`,
  `PORT=8004`, `LOG_LEVEL="INFO"`; `SQLALCHEMY_DATABASE_URL` property
  (`postgresql+asyncpg://…`). `model_config = SettingsConfigDict(env_file=".env")`.
- `src/db/session.py` — async engine/`AsyncSessionLocal`/`get_db`/`init_db`
  (connectivity `SELECT 1` only — schema owned by Alembic, no `create_all`),
  mirroring test-management-service `session.py`. `Base = declarative_base()`.
- Empty package dirs with `__init__.py`: `src/v1/routes/`, `src/services/`,
  `src/repositories/`, `src/models/`, `src/schemas/`, `src/config/`, `src/db/`,
  `src/v1/`, `src/`.
- `requirements.txt` — fastapi, uvicorn[standard], SQLAlchemy, asyncpg,
  psycopg2-binary (for the start.sh wait-loop + Alembic offline), pydantic,
  pydantic-settings, python-dotenv, alembic, httpx.
- `requirements-dev.txt` — `-r requirements.txt` + pytest, pytest-cov, ruff
  (same pins as user-service).
- `Dockerfile` — copy test-management-service's multi-stage Dockerfile
  (base→test→production), EXPOSE 8004, `chmod +x start.sh`, non-root `appuser`,
  HEALTHCHECK curl `:8004/health`, `CMD ["./start.sh"]`.
- `pytest.ini` (`pythonpath=.`, `testpaths=tests`, `-q`), `conftest.py`
  (hermetic env defaults so `Settings()` import doesn't need a real DB),
  `.coveragerc` (`source=.`, omit tests/conftest/seed, `fail_under` = measured
  baseline from M5's smoke run).
- **Commit:** `feat(w2-m10): scaffold reporting-and-analytics-service (standard layout)`

### M2 — `reporting-postgres` datastore (detail step 2)
`docker-compose.yml`: add a second Postgres instance.
- `reporting-postgres`: `postgres:15-alpine`, container `rev-eval-reporting-postgres`,
  env `POSTGRES_USER/PASSWORD/DB` from `REPORTING_POSTGRES_*` (defaults
  `root`/`root`/`eval_ai_reporting`), host port `5433:5432`, volume
  `reporting_postgres_data`, `pg_isready` healthcheck (same shape as `postgres`).
- Add `reporting_postgres_data:` to top-level `volumes:`.
- Update `.env.example` with a `Reporting PostgreSQL` block
  (`REPORTING_POSTGRES_USER/PASSWORD/DB`).
- **Commit:** `feat(w2-m10): add dedicated reporting-postgres instance + env`

### M3 — Compose wiring for the service (detail step 3)
`docker-compose.yml`: add `reporting-and-analytics-service`:
- build context `./services/reporting-and-analytics-service`, container
  `rev-eval-reporting-analytics`, `restart: unless-stopped`.
- env: `DB_HOST: reporting-postgres`, `DB_PORT: 5432`, `DB_USERNAME/PASSWORD/NAME`
  from `REPORTING_POSTGRES_*`, `SERVICE_NAME`, `PORT: 8004`,
  `ALLOW_ORIGINS: http://localhost:3000`, `LOG_LEVEL`.
- ports `8004:8004`.
- `depends_on: reporting-postgres: condition: service_healthy`.
- healthcheck curl `:8004/health` (interval/timeout/retries/start_period like
  test-management-service).
- **Commit:** `feat(w2-m10): wire reporting service into compose (healthcheck + dep)`

### M4 — Alembic (detail step 4)
From `services/reporting-and-analytics-service/`:
- `alembic.ini` — copy test-management-service's (blank `sqlalchemy.url`,
  `script_location=%(here)s/alembic`, `prepend_sys_path=.`, logging blocks).
- `alembic/env.py` — copy + adapt: import `Base` from `src.db.session` (no model
  imports yet — add a comment that W4-F1 imports its models here), async engine,
  runtime URL resolution (`DATABASE_URL` → asyncpg), `compare_type=True`,
  `include_object` filter (parity).
- `alembic/script.py.mako`, `alembic/README` — copy from test-management-service.
- `alembic/versions/0001_baseline.py` — **empty baseline**: `revision="0001"`,
  `down_revision=None`, `upgrade()`/`downgrade()` bodies `pass` with a comment
  ("empty baseline — reporting tables land in W4-F1"). Establishes the chain and
  causes `alembic upgrade head` to create `alembic_version`.
- `start.sh` — Postgres wait-loop (psycopg2 one-liner, `DB_*` env), then
  `alembic upgrade head || exit 1`, then `exec python main.py`. No `stamp` branch
  (fresh datastore). `chmod +x` handled in Dockerfile.
- **Commit:** `feat(w2-m10): initialize Alembic env + empty 0001 baseline + start.sh`

### M5 — CI matrix parity (locked decision 2)
`.github/workflows/ci-pipeline.yml`:
- add `reporting-and-analytics-service: ['services/reporting-and-analytics-service/**']`
  to the `changes` job `filters`.
- add `"reporting-and-analytics-service"` to the `all` JSON list (line ~42).
- Add a minimal `tests/test_smoke.py` (+ `tests/__init__.py`) so the coverage
  step runs and Ruff has something to lint: assert settings import + health
  handler returns `{"status": "ok"}`, `SQLALCHEMY_DATABASE_URL` builds the
  asyncpg URL. Set `.coveragerc` `fail_under` to the measured baseline from this
  run (likely high — tiny surface).
- Confirm `ruff check .` clean and `docker build --target test` passes (the
  Dockerfile test stage runs pytest).
- **Commit:** `ci(w2-m10): add reporting service to backend matrix + smoke tests`

### M6 — Requirements review + docs
- Re-read detail doc Steps 1–5 + spec §5; verify each against the diff (cite
  file:line / commit). Note step 5 N/A-at-scaffold with rationale.
- Detail doc: check off steps 1–4, mark step 5 deferred-to-W4-F1, add Evidence
  (paths, commits, this plan link), set Status ✅ Completed.
- `docs/FEATURE_STATUS.md`: W2-M10 row → ✅ Completed, update "Last assessed".
- `rev-eval/CLAUDE.md` + root `CLAUDE.md`: update the services table (reporting
  port 8004, store Postgres; "2 Postgres instances"; drop "empty by design" note).
- **Commit:** `docs(w2-m10): mark milestone complete + update topology docs`

## Testing & validation

1. **Per-service pytest:** from `services/reporting-and-analytics-service/`,
   `pip install -r requirements-dev.txt && pytest --cov` — green, coverage ≥
   `.coveragerc` `fail_under`.
2. **Ruff:** `ruff check .` clean in the new service.
3. **Docker test stage:** `docker build --target test .` passes (in-image pytest).
4. **Fresh stack:** `docker compose down -v && docker compose up --build` —
   `reporting-postgres` healthy; reporting service logs `alembic upgrade head`
   creating `alembic_version` (rev `0001`); `/health` on `:8004` returns `ok`;
   service reaches healthy. Confirm the existing 4 services + shared `postgres`
   still come up (no port/volume clash).
5. **Alembic chain:** `alembic history` shows `0001`; `alembic current` = `0001`
   after upgrade; `alembic downgrade base && alembic upgrade head` round-trips.

**Pass bar:** all of the above green, and detail-doc steps 1–4 satisfied with
evidence (step 5 explicitly deferred).

## Push gate

Push `richardh-feat-W2M10` to origin **only if** tests pass **and** the
requirements review confirms steps 1–4 met (step 5 documented N/A). Otherwise
stop, leave the branch local, report what's outstanding.

## Risks / watch-items
- **Port/volume clash:** new Postgres must use a distinct host port (5433),
  volume (`reporting_postgres_data`), and container name — verify the shared
  `postgres` is untouched.
- **Empty baseline correctness:** `0001` with `down_revision=None` + `pass`
  bodies is valid Alembic; verify `upgrade head` actually creates
  `alembic_version` (it does once any revision is applied).
- **Trivy gate:** the new Dockerfile must carry the same base-image tooling
  upgrade line, or CI's Trivy CRITICAL/HIGH gate fails on day one.
- **Scope:** no domain models/endpoints — resist adding any (W4-F1 owns them).
