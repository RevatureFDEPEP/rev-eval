# Plan: Reporting and Analytics Service — Read-Heavy GET Endpoints

## Context

The `services/reporting-and-analytics-service/` folder exists but is empty. The candidate results page needs three injected sections: a summary envelope, a paginated attempt history, and per-entity aggregates. This plan wires up the full service: data access strategy, two GET endpoints, CORS, Alembic baseline, ADR doc, and unit tests.

---

## Data Access Strategy

**Decision: read-only connection to the shared PostgreSQL instance — no mirror table.**

The project runs a single `postgres:15-alpine` container. Both `user-service` and `test-management-service` already connect to `eval_ai_dev` on the same host/credentials. There is no event bus (no SQS/Kafka configured per CLAUDE.md). A mirror table would require a polling scheduler, watermark management, and sync drift handling — all complexity with no isolation benefit when the source is already a shared instance.

The reporting service declares SQLAlchemy models that map to the *existing* `sessions` and `session_answers` tables (owned by test-management-service) and issues only `SELECT` queries. Alembic is wired up as a baseline-only setup for forward extensibility.

**Key constraint:** `Session.status` uses a Postgres enum type named `sessionstatus` created by test-management-service. The reporting service must redeclare that column with `create_type=False` to avoid attempting a duplicate `CREATE TYPE`.

---

## Directory Layout

```
services/reporting-and-analytics-service/
├── README.md                          (exists)
├── Dockerfile
├── requirements.txt
├── dev-requirements.txt
├── pytest.ini
├── alembic.ini
├── main.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── a1b2c3d4_initial_reporting_service.py
├── src/
│   ├── __init__.py
│   ├── config/
│   │   └── settings.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py           ← read-only mapping of sessions table
│   │   └── session_answer.py    ← read-only mapping of session_answers table
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── report_schema.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── report_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── report_service.py
│   └── v1/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           └── report_route.py
└── tests/
    ├── conftest.py
    └── test_report_repository.py
```

---

## File-by-File Implementation

### `requirements.txt`
Mirror test-management-service. Omit auth/bcrypt/jose packages. Include:
`fastapi`, `uvicorn[standard]`, `SQLAlchemy`, `pydantic`, `pydantic-settings`, `python-dotenv`, `alembic`, `psycopg2-binary`, `asyncpg`

### `dev-requirements.txt`
`pytest`, `pytest-asyncio`, `pytest-cov`, `aiosqlite`

### `pytest.ini`
```ini
[pytest]
asyncio_mode = auto
pythonpath = .
testpaths = tests
```

### `src/config/settings.py`
Identical pattern to test-management-service's `config/settings.py`. Key fields:
- `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`
- `ALLOW_ORIGINS: str = "http://localhost:3000"`
- `PORT: int = 8004`
- Property `SQLALCHEMY_DATABASE_URL` builds `postgresql+psycopg2://...` string

### `src/db/session.py`
Async engine with `asyncpg`. `init_db()` runs `SELECT 1` to verify connectivity — does **not** call `Base.metadata.create_all` (tables are owned by test-management-service). Standard `get_db()` async generator for FastAPI `Depends`.

### `src/models/session.py`
Maps to the existing `sessions` table. Critical differences from the source model:
- No `ForeignKey("tests.id")` on `test_id` — avoids cross-service FK constraint
- `Enum(SessionStatus, name="sessionstatus", create_type=False)` — prevents duplicate type creation

Columns: `session_id (UUID PK)`, `test_id (Integer)`, `user_id (Integer)`, `session_token (String)`, `server_now (DateTime)`, `expires_at (DateTime)`, `status (Enum)`, `current_index (Integer)`, `question_ids (JSON)`, `submitted_at (DateTime, nullable)`

### `src/models/session_answer.py`
Maps to the existing `session_answers` table. No FK to `sessions` declared (not needed for reads; avoids mapper conflicts with the separate Base).

Columns: `id (Integer PK)`, `session_id (UUID)`, `question_id (String)`, `question_index (Integer)`, `submitted_answers (JSON)`, `earned_points (Float)`, `max_points (Float)`, `is_correct (Boolean)`, `answered_at (DateTime)`. Includes `UniqueConstraint("session_id", "question_index", name="uq_session_answer_index")`.

### `src/schemas/report_schema.py`

**`UserSummaryResponse`** (Pydantic BaseModel):
- `user_id: int`
- `total_attempts: int`
- `average_score: float | None`  — avg per-session score ratio; null if 0 attempts
- `best_score: float | None`     — max per-session score ratio
- `total_time_spent: float | None` — sum of (submitted_at − server_now) in seconds
- `most_recent_attempt: AttemptItem | None`

**`AttemptItem`** (Pydantic BaseModel, `from_attributes=True`):
- `session_id: UUID`, `test_id: int`, `user_id: int`, `status: SessionStatus`
- `server_now: datetime`, `submitted_at: datetime | None`, `expires_at: datetime`
- `score_ratio: float | None` — derived per-session sum(earned)/sum(max)

**`PaginatedAttemptsResponse`**:
- `items: list[AttemptItem]`, `total: int`, `page: int`, `size: int`

**`AttemptFilter`** (Pydantic `dataclass` — FastAPI auto-converts fields to query params):
- `page: int = 1`
- `size: int = 20`  (clamped to max 100 in service layer)
- `test_id: int | None = None`
- `from_date: date | None = None`
- `to_date: date | None = None`
- `status: SessionStatus | None = None`
- `sort: str = "server_now:desc"` — validated pattern `field:direction`; allowed fields: `{server_now, submitted_at, expires_at, score_ratio}`

### `src/repositories/report_repository.py`

**`get_user_summary(db, user_id: int) → dict`**

Single query using a CTE:
1. CTE `session_scores` — LEFT JOIN `sessions` → `session_answers` GROUP BY `session_id`, computing:
   - `score_ratio = CASE WHEN sum(max_points) > 0 THEN sum(earned_points)/sum(max_points) ELSE NULL END`
   - `time_spent = EXTRACT(EPOCH FROM (submitted_at - server_now))`  (null when submitted_at is null)
2. Outer SELECT aggregates over `session_scores WHERE user_id = :uid`:
   - `func.count(*)` → `total_attempts`
   - `func.avg(score_ratio)` → `average_score`  (AVG ignores NULLs natively)
   - `func.max(score_ratio)` → `best_score`
   - `func.sum(time_spent)` → `total_time_spent`
3. Subquery for `most_recent_attempt` — `SELECT * FROM sessions WHERE user_id = :uid ORDER BY server_now DESC LIMIT 1`

SQLite test note: `EXTRACT(EPOCH FROM ...)` is Postgres-only. Detect engine dialect and use `(func.julianday(submitted_at) - func.julianday(server_now)) * 86400` for SQLite. Abstract as `_time_diff_seconds(col_a, col_b)` helper inside the repository.

**`list_attempts(db, user_id: int, filters: AttemptFilter) → tuple[list, int]`**

Reuse the `session_scores` CTE. Build base statement with `WHERE user_id = :uid`, then conditionally append:
- `.where(Session.test_id == filters.test_id)` if provided
- `.where(Session.server_now >= filters.from_date)` if provided
- `.where(Session.server_now < filters.to_date + timedelta(days=1))` if provided
- `.where(Session.status == filters.status)` if provided

Sort: parse `filters.sort` → map field name to CTE column alias → `.order_by(col.asc()|.desc())`.

Pagination: execute a `COUNT(*)` with same filters (no limit/offset) for `total`, then execute the paginated query with `.offset((page-1)*size).limit(size)`.

### `src/services/report_service.py`
Thin orchestration layer. Calls repository, assembles Pydantic response schemas. Validates the `sort` parameter — raises `HTTPException(422)` on invalid field or direction. Clamps `size` to `min(filters.size, 100)`. Returns zero-value `UserSummaryResponse` (not 404) when a user has no sessions.

### `src/v1/routes/report_route.py`
```python
router = APIRouter(prefix="/reports", tags=["Reports"])

GET /reports/user/{user_id}
    → response_model=UserSummaryResponse
    → Depends(get_db)

GET /reports/user/{user_id}/attempts
    → response_model=PaginatedAttemptsResponse
    → filters: AttemptFilter = Depends()
    → Depends(get_db)
```
`user_id` path param typed as `int` — consistent with `Integer` PK in user-service and test-management-service.

### `main.py`
- `load_dotenv()` at top
- `CORSMiddleware` with `allow_origins` parsed from `settings.ALLOW_ORIGINS` (comma-split, defaults to `http://localhost:3000`)
- `app.include_router(report_router, prefix="/v1/api")`
- `/health` GET endpoint
- `@app.on_event("startup")` → `await init_db()`
- `uvicorn.run(...)` on `settings.PORT` (default 8004)

---

## Alembic Setup

Copy `alembic.ini` and `alembic/env.py` from test-management-service verbatim, adjusting imports to reference reporting service models. The `env.py` imports `Session` and `SessionAnswer` to register them with `Base.metadata`.

**`alembic/versions/a1b2c3d4_initial_reporting_service.py`**:
```python
"""Initial baseline — no tables created (service reads existing tables)

Revision ID: a1b2c3d4
Revises: 
"""
revision = "a1b2c3d4"
down_revision = None

def upgrade(): pass
def downgrade(): pass
```

---

## ADR Document

**File:** `docs/reporting-analytics-adr.md`

Structure:
- **Status:** Accepted
- **Context:** Need per-user analytics queries against sessions/session_answers tables; no event bus available
- **Decision:** Read-only shared PostgreSQL connection; SQLAlchemy models map existing tables without creating them; Alembic baseline-only
- **Alternatives considered:**
  1. Separate DB + mirror table + polling (rejected: sync lag, watermark complexity, failure modes)
  2. Event sourcing via SQS (rejected: out of scope, requires infra changes)
- **Consequences:** Schema changes to sessions/session_answers in test-management-service must account for reporting queries; Alembic baseline provides upgrade path to a full isolated schema if needed later

---

## Tests

**`tests/conftest.py`** — mirrors test-management-service's conftest exactly:
- Set all env vars via `os.environ.setdefault` before any imports
- `@pytest_asyncio.fixture async def db()` — creates in-memory SQLite DB, imports both models to register with Base, calls `create_all`, yields session, calls `drop_all`

**`tests/test_report_repository.py`** — test cases:

*Summary aggregate tests:*
- `test_summary_no_sessions_returns_zero_total` — `total_attempts=0`, scores/time `None`
- `test_summary_single_completed_session_all_correct` — `total_attempts=1`, `average_score=1.0`, `best_score=1.0`, `total_time_spent` matches (submitted_at − server_now)
- `test_summary_multiple_sessions_correct_average` — seed 3 sessions with score ratios [0.5, 0.75, 1.0]; assert `average_score ≈ 0.75`, `best_score ≈ 1.0`
- `test_summary_session_without_answers_excluded_from_average` — session with no answer rows; score_ratio is NULL and excluded from AVG
- `test_summary_most_recent_attempt_is_latest_by_server_now` — 3 sessions with different `server_now`; assert `most_recent_attempt.session_id` matches the latest

*Pagination and filter tests:*
- `test_list_attempts_default_page_returns_20_of_25` — seed 25; assert `len(items)==20`, `total==25`, `page==1`, `size==20`
- `test_list_attempts_page_2_returns_remaining_5` — `page=2, size=20`; assert `len(items)==5`
- `test_list_attempts_size_clamp_enforced` — `size=200`; assert `len(items) <= 100`
- `test_list_attempts_filter_by_test_id` — seed for test_id 1 and 2; filter 1; all items have `test_id==1`
- `test_list_attempts_filter_by_from_date` — no items before `from_date`
- `test_list_attempts_filter_by_to_date` — no items after `to_date`
- `test_list_attempts_filter_by_status_completed` — all items have `status==COMPLETED`
- `test_list_attempts_sort_asc_server_now` — `items[i].server_now <= items[i+1].server_now`
- `test_list_attempts_sort_desc_score_ratio` — `items[i].score_ratio >= items[i+1].score_ratio` (NULLs last)
- `test_list_attempts_user_id_isolation` — query user 1; no items belong to user 2

---

## Docker-Compose Addition

Add after `test-management-service` block in `docker-compose.yml`:

```yaml
  reporting-and-analytics-service:
    build:
      context: ./services/reporting-and-analytics-service
      dockerfile: Dockerfile
    container_name: rev-eval-reporting
    restart: unless-stopped
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USERNAME: ${POSTGRES_USER:-postgres}
      DB_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      DB_NAME: ${POSTGRES_DB:-eval_ai_dev}
      SERVICE_NAME: reporting-and-analytics-service
      PORT: 8004
      ALLOW_ORIGINS: http://localhost:3000
    ports:
      - "8004:8004"
    depends_on:
      postgres:
        condition: service_healthy
      test-management-service:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
```

Also add `reporting-and-analytics-service: condition: service_healthy` to `api-gateway`'s `depends_on` block.

No new `.env.example` variables needed — the service reuses existing `POSTGRES_*` variables.

---

## Verification

1. Run unit tests: `cd services/reporting-and-analytics-service && pytest tests/ -v`
2. Full stack: `docker compose up --build` — confirm `rev-eval-reporting` starts healthy
3. Hit `http://localhost:8004/health` → `{"status": "ok"}`
4. With seeded data from test-management-service's `seed_db.py`, call:
   - `GET http://localhost:8004/v1/api/reports/user/1` → summary envelope
   - `GET http://localhost:8004/v1/api/reports/user/1/attempts?page=1&size=5` → paginated list
   - `GET http://localhost:8004/v1/api/reports/user/1/attempts?status=COMPLETED&sort=server_now:asc` → filtered + sorted
5. Verify CORS: browser fetch from `http://localhost:3000` to the reporting service should not be blocked
