# W4-F1 — Candidate Results Reporting Endpoints

## Context

W3-F2 writes scored `quiz_sessions` + `session_answers` into `eval_ai_dev` (test-management DB), but no endpoint serves those results to candidates. The reporting-and-analytics-service is a stub (only `/health`). This feature builds the two read-heavy GET endpoints that W4-F2 (results page) depends on.

Gap from W3-F6 notes: a just-taken quiz shows no score anywhere — this feature closes that.

---

## Data Access Decision: Direct-Read (Shared Postgres)

The reporting service will open a **second SQLAlchemy engine** pointing to `eval_ai_dev` (same Postgres host/port/user/pass as the reporting service, different `DB_NAME`). This lets us write the required `func.avg/count/sum` aggregate queries directly without event sourcing or sync lag.

Trade-offs go in `docs/adr/001-reporting-data-access.md`.

**No new tables in `reporting_dev` → Alembic migration 0002 is a no-op documenting the decision.**

---

## Files to Create (15 new)

All paths relative to `services/reporting-and-analytics-service/` unless noted.

| File | Purpose |
|---|---|
| `src/db/__init__.py` | package marker |
| `src/db/session.py` | `EvalAiBase`, sync `eval_ai_engine`, `get_eval_ai_db()` dep |
| `src/models/__init__.py` | package marker |
| `src/models/quiz_session.py` | read-only mirror: `QuizSession`, `SessionStatus` |
| `src/models/session_answer.py` | read-only mirror: `SessionAnswer` |
| `src/schemas/__init__.py` | package marker |
| `src/schemas/reports.py` | `UserSummary`, `AttemptItem`, `PaginatedAttempts`, `AttemptsFilter` |
| `src/v1/__init__.py` | package marker |
| `src/v1/routes/__init__.py` | package marker |
| `src/v1/routes/reports.py` | two GET endpoints |
| `tests/__init__.py` | package marker |
| `tests/conftest.py` | SQLite in-memory fixture, `get_eval_ai_db` override |
| `tests/test_reports.py` | pagination, filter, aggregate assertions |
| `migrations/versions/0002_direct_read_adr.py` | empty no-op migration |
| `docs/adr/001-reporting-data-access.md` | ADR (create `docs/adr/` dir too) |

---

## Files to Modify (4 existing)

| File | Change |
|---|---|
| `src/config/settings.py` | Add `EVAL_AI_DB_NAME: str = "eval_ai_dev"` + `EVAL_AI_SQLALCHEMY_DATABASE_URL` property |
| `main.py` | Tighten CORS to `http://localhost:3000`; include router at prefix `/v1/api` |
| `requirements.txt` | Add `pytest`, `httpx`, `pytest-cov` |
| `services/api-gateway-service/main.py` | Add `"reporting-and-analytics-service": 8004` to `SERVICE_PORTS`; add reports pattern to `ROUTES` |

---

## Implementation Detail

### `src/config/settings.py` additions
```python
EVAL_AI_DB_NAME: str = "eval_ai_dev"

@property
def EVAL_AI_SQLALCHEMY_DATABASE_URL(self) -> str:
    return (
        f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
        f"@{self.DB_HOST}:{self.DB_PORT}/{self.EVAL_AI_DB_NAME}"
    )
```
Reuses same host/port/user/pass; only DB name differs.

### `src/db/session.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config.settings import settings

EvalAiBase = declarative_base()

eval_ai_engine = create_engine(settings.EVAL_AI_SQLALCHEMY_DATABASE_URL)
EvalAiSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eval_ai_engine)

def get_eval_ai_db():
    db = EvalAiSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Read-only mirror models (use `EvalAiBase`, NOT reporting_dev Base)

`src/models/quiz_session.py` — columns needed:
`id`, `test_id`, `user_id`, `status` (SessionStatus enum), `server_now`, `submitted_at`, `created_at`

`src/models/session_answer.py` — columns needed:
`id`, `session_id`, `score`

These reflect the `quiz_sessions` / `session_answers` tables from test-management-service. No FK relationships needed.

### `src/schemas/reports.py`
```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from fastapi import Query
from pydantic import BaseModel
from src.models.quiz_session import SessionStatus

class MostRecentAttempt(BaseModel):
    session_id: str
    test_id: int
    submitted_at: Optional[datetime]
    score: Optional[float]

class UserSummary(BaseModel):
    user_id: int
    total_attempts: int
    avg_score: Optional[float]
    best_score: Optional[float]
    total_time_spent_seconds: Optional[float]  # null on SQLite; works on PG
    most_recent_attempt: Optional[MostRecentAttempt]

class AttemptItem(BaseModel):
    session_id: str
    test_id: int
    status: str
    submitted_at: Optional[datetime]
    score: Optional[float]
    created_at: datetime

class PaginatedAttempts(BaseModel):
    items: list[AttemptItem]
    total: int
    page: int
    size: int

@dataclass
class AttemptsFilter:
    page: int = Query(1, ge=1)
    size: int = Query(20, ge=1, le=100)
    test_id: Optional[int] = Query(None)
    from_: Optional[date] = Query(None, alias="from")
    to: Optional[date] = Query(None)
    status: Optional[SessionStatus] = Query(None)
    sort: str = Query("submitted_at:desc")
```

### `src/v1/routes/reports.py` — core query logic

**GET /reports/user/{user_id} (summary):**
```python
# session_scores subquery
session_scores = (
    select(SessionAnswer.session_id, func.sum(SessionAnswer.score).label("total_score"))
    .group_by(SessionAnswer.session_id)
    .subquery()
)

# main aggregate query (single round-trip)
row = db.execute(
    select(
        func.count(QuizSession.id).label("total_attempts"),
        func.avg(session_scores.c.total_score).label("avg_score"),
        func.max(session_scores.c.total_score).label("best_score"),
        func.sum(
            func.extract("epoch", QuizSession.submitted_at - QuizSession.server_now)
        ).label("total_time_spent"),
    )
    .outerjoin(session_scores, session_scores.c.session_id == QuizSession.id)
    .where(QuizSession.user_id == user_id, QuizSession.status == SessionStatus.SUBMITTED)
).one()

# separate query for most-recent row
latest = db.execute(
    select(QuizSession, session_scores.c.total_score)
    .outerjoin(session_scores, session_scores.c.session_id == QuizSession.id)
    .where(QuizSession.user_id == user_id, QuizSession.status == SessionStatus.SUBMITTED)
    .order_by(QuizSession.submitted_at.desc())
    .limit(1)
).first()
```

**GET /reports/user/{user_id}/attempts (paginated):**
- Build base query with outer join to session_scores
- Apply filters: test_id, status, from/to date range
- Count total via `select(func.count()).select_from(query.subquery())`
- Apply sort: split `filters.sort` on `:`, whitelist fields (`submitted_at`, `created_at`, `score`)
- Apply `.offset((page-1)*size).limit(size)`

**Allowed sort fields:** `{"submitted_at", "created_at", "score"}` — raise 400 for unknown field.

### `main.py` changes
```python
from src.v1.routes.reports import router as reports_router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # tighten from "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router, prefix="/v1/api")
```

### Gateway changes (`services/api-gateway-service/main.py`)
```python
SERVICE_PORTS = {
    ...
    "reporting-and-analytics-service": 8004,   # ADD
}

ROUTES = [
    ...
    {"pattern": r"^/v1/api/reports(/.*)?$", "service": "reporting-and-analytics-service"},  # ADD
]
```

---

## Testing Pattern (`tests/conftest.py`)

```python
import os
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "reporting")
os.environ.setdefault("EVAL_AI_DB_NAME", "eval_ai_dev")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient
from main import app
from src.db.session import EvalAiBase, get_eval_ai_db
from src.models.quiz_session import QuizSession, SessionStatus  # noqa: F401
from src.models.session_answer import SessionAnswer              # noqa: F401

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    EvalAiBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    EvalAiBase.metadata.drop_all(engine)

@pytest.fixture
def client(db):
    app.dependency_overrides[get_eval_ai_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Test assertions in `tests/test_reports.py`:**
- Summary on empty DB → `total_attempts=0`, `avg_score=None`, `most_recent_attempt=None`
- Seed 3 SUBMITTED sessions + answers → assert `total_attempts=3`, `avg_score` and `best_score` match seeded values
- `total_time_spent_seconds` → assert `>= 0 or is None` (SQLite dialect doesn't support `EXTRACT(EPOCH ...)`)
- Paginate 25 seeded sessions (page=1/size=20 → 20 items, total=25; page=2 → 5 items)
- Filter `test_id=1` → only sessions for that test
- Filter `status=SUBMITTED` → exclude non-submitted
- Filter `from`/`to` date range → correct subset
- Sort `score:asc` → ascending order

---

## Verification

```bash
# 1. Lint
source .venv/bin/activate
ruff check services/reporting-and-analytics-service/
ruff format services/reporting-and-analytics-service/

# 2. Unit tests
pytest services/reporting-and-analytics-service/tests/ -v

# 3. Alembic (from service dir)
cd services/reporting-and-analytics-service
alembic upgrade head

# 4. Integration (requires docker compose up)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/api/reports/user/1
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/api/reports/user/1/attempts?page=1&size=5"
```

Update `docs/features/w4-f1-results-reporting-endpoints.md` and `docs/FEATURE_STATUS.md` in the same PR (check off all 6 steps, set status ✅).
