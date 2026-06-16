# W3-F1 Implementation Plan — Quiz Session Creation Backend

**Status:** ❌ Not Started  
**Tracker:** `docs/features/w3-f1-quiz-session-backend.md`  
**Spec:** `docs/feature_specs/days_11_15_features.md` §1  
**Branch:** `tianyac-feat-session`  
**Updated:** 2026-06-16

---

## Goal

`POST /v1/api/sessions` in test-management-service that:
1. Mints an opaque session token
2. Records `server_now` and `expires_at` in Postgres (client never computes timing)
3. Samples questions from question-management-service via httpx
4. Returns session contract + first question to the client

---

## Baseline Gaps

| Gap | Detail |
|-----|--------|
| Alembic not initialized | No `alembic.ini`, no `migrations/` in test-management-service |
| `QuizSession` model missing | No model, no table |
| `POST /sessions` missing | No route, no handler |
| `GET /questions/sample` missing | question-management-service has no `$sample` endpoint |
| Gateway unaware of `/sessions` | Pattern not in ROUTES list |

`httpx` already in `requirements.txt`. No new dependency needed.

---

## Dependency Check

- **Blocked on:** W2-F7 Alembic revision `0003` at head. If `0003` doesn't exist, initialize Alembic fresh (Step 0).
- **Unblocks:** W3-F2 (needs `quiz_sessions` table + `current_index`), W3-F3 (page calls `POST /sessions` on load).

---

## Step 0 — Initialize Alembic (one-time)

```bash
cd services/test-management-service
alembic init migrations
```

**Edit `alembic.ini`** — clear `sqlalchemy.url` (env.py will set it):
```ini
script_location = migrations
# sqlalchemy.url intentionally blank — overridden in env.py
```

**Replace `migrations/env.py`** with async-compatible version:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from src.db.session import Base
from src.config.settings import settings

# Register all models so autogenerate sees them
import src.models.test            # noqa: F401
import src.models.test_submission # noqa: F401
import src.models.skill           # noqa: F401
import src.models.test_skill      # noqa: F401
import src.models.quiz_session    # noqa: F401  (created in Step 1)

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_db_url = settings.SQLALCHEMY_DATABASE_URL
if _db_url.startswith("postgresql://"):
    ASYNC_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://")
elif _db_url.startswith("postgresql+psycopg2://"):
    ASYNC_URL = _db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
else:
    ASYNC_URL = _db_url


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    engine = create_async_engine(ASYNC_URL)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=ASYNC_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_migrations_online())
```

---

## Step 1 — QuizSession SQLAlchemy Model

**Create:** `services/test-management-service/src/models/quiz_session.py`

```python
import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID

from src.db.session import Base


class SessionStatus(str, enum.Enum):
    STARTED     = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED   = "SUBMITTED"
    EXPIRED     = "EXPIRED"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    test_id       = Column(Integer, ForeignKey("tests.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("test_submissions.id"), nullable=True)
    user_id       = Column(Integer, nullable=False)
    status        = Column(Enum(SessionStatus), default=SessionStatus.STARTED, nullable=False)
    current_index = Column(Integer, default=0, nullable=False)
    question_ids  = Column(JSON, nullable=False)  # list[str] of MongoDB ObjectIds (ordered)
    server_now    = Column(DateTime, nullable=False)
    expires_at    = Column(DateTime, nullable=False)
    submitted_at  = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Also** import it in `src/db/session.py` inside `init_db()` so `create_all` registers it:

```python
async def init_db():
    from src.models import quiz_session  # noqa: F401
    ...
```

---

## Step 2 — Alembic Migration

```bash
# From services/test-management-service/
alembic revision --autogenerate -m "0004_add_quiz_sessions"
alembic upgrade head
```

Review the generated file — confirm it creates `quiz_sessions` with all columns above. Name matches spec convention (`0004_` after W2-F7's `0003`).

---

## Step 3 — Sample Endpoint in question-management-service

No `$sample` endpoint exists. Add it.

**Add to `services/question-management-service/src/services/question_service.py`:**

```python
@staticmethod
async def sample_questions(n: int, skills: Optional[List[str]] = None) -> List[dict]:
    pipeline: list = []
    if skills:
        pipeline.append({"$match": {"skills": {"$in": skills}}})
    pipeline.append({"$sample": {"size": n}})
    results = await Question.aggregate(pipeline).to_list()
    for doc in results:
        doc["_id"] = str(doc["_id"])  # ObjectId → str for JSON
    return results
```

**Add to `services/question-management-service/src/v1/routes/question_routes.py`:**

```python
@router.get("/sample")
async def sample_questions(
    n: int = Query(20, ge=1, le=100),
    skills: Optional[str] = Query(None, description="Comma-separated skill names"),
):
    skill_list = [s.strip() for s in skills.split(",")] if skills else None
    return await QuestionService.sample_questions(n=n, skills=skill_list)
```

> The existing gateway regex `^/v1/api/questions(/.*)?$` already covers this route. No gateway change needed here.

---

## Step 4 — httpx Singleton

**Create:** `services/test-management-service/src/utils/http_client.py`

```python
import httpx
from src.config.settings import settings

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.QUESTION_SERVICE_URL,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    return _client
```

**Add to `src/config/settings.py`:**

```python
QUESTION_SERVICE_URL: str = "http://question-management-service:8003"
```

For local dev outside Compose, override with `QUESTION_SERVICE_URL=http://localhost:8003` in `.env`.

---

## Step 5 — Pydantic Schemas

**Create:** `services/test-management-service/src/schemas/quiz_session_schema.py`

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SessionCreate(BaseModel):
    test_id: int
    submission_id: Optional[int] = None


class QuizQuestionOut(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    difficulty: str
    options: Optional[List[dict]] = None
    # correct_answers intentionally absent — never sent to client during quiz


class SessionRead(BaseModel):
    session_id: str       # UUID as str
    session_token: str
    test_id: int
    user_id: int
    status: str
    current_index: int
    server_now: datetime
    expires_at: datetime
    first_question: Optional[QuizQuestionOut]

    class Config:
        from_attributes = True
```

---

## Step 6 — POST /sessions Handler

**Create:** `services/test-management-service/src/v1/routes/quiz_session_route.py`

```python
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.quiz_session import QuizSession
from src.repositories.test_repository import TestRepository
from src.schemas.quiz_session_schema import QuizQuestionOut, SessionCreate, SessionRead
from src.utils.dependencies import get_current_user_from_headers
from src.utils.http_client import get_http_client

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionRead, status_code=201)
async def create_session(
    body: SessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
):
    test = await TestRepository.get_by_id(db, body.test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Propagate correlation ID to downstream call
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))

    # Sample questions via httpx
    client = get_http_client()
    skill_names = [ts.skill.name for ts in (test.test_skills or [])]
    params = {"n": test.number_of_questions or 20}
    if skill_names:
        params["skills"] = ",".join(skill_names)

    try:
        resp = await client.get(
            "/v1/api/questions/sample",
            params=params,
            headers={"X-Correlation-Id": correlation_id},
        )
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Question service error: {exc}")

    sampled: list = resp.json()
    if not sampled:
        raise HTTPException(status_code=422, detail="No questions available for this test")

    # Server-authoritative timing
    server_now = datetime.utcnow()
    duration_secs = test.duration.total_seconds() if test.duration else 3600
    expires_at = server_now + timedelta(seconds=duration_secs)

    session = QuizSession(
        session_token=secrets.token_hex(32),
        test_id=body.test_id,
        submission_id=body.submission_id,
        user_id=current_user["id"],
        question_ids=[q["_id"] for q in sampled],
        server_now=server_now,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    raw_q = sampled[0]
    first_q = QuizQuestionOut(
        question_id=raw_q["_id"],
        question_text=raw_q["question_text"],
        question_type=raw_q["type"],
        difficulty=raw_q.get("difficulty", "medium"),
        options=raw_q.get("options"),
    )

    return SessionRead(
        session_id=str(session.id),
        session_token=session.session_token,
        test_id=session.test_id,
        user_id=session.user_id,
        status=session.status.value,
        current_index=session.current_index,
        server_now=session.server_now,
        expires_at=session.expires_at,
        first_question=first_q,
    )
```

---

## Step 7 — Register Route + Gateway Config

**`services/test-management-service/main.py`** — add:

```python
from src.v1.routes.quiz_session_route import router as quiz_session_router
...
app.include_router(quiz_session_router, prefix="/v1/api")
```

**`services/api-gateway-service/main.py`** — add to `ROUTES` list before any catch-all:

```python
{"pattern": r"^/v1/api/sessions(/.*)?$", "service": "test-management-service"},
```

---

## Step 8 — Unit Tests

**Create:** `services/test-management-service/tests/test_quiz_session.py`

```python
import pytest
from datetime import datetime, timedelta
from uuid import UUID

from src.models.quiz_session import QuizSession, SessionStatus
from src.schemas.quiz_session_schema import SessionCreate, SessionRead


class TestQuizSessionModel:
    async def test_defaults(self, db):
        s = QuizSession(
            session_token="tok",
            test_id=1,
            user_id=42,
            question_ids=["id1", "id2"],
            server_now=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(s); await db.commit()
        assert s.id is not None
        assert isinstance(s.id, UUID)
        assert s.current_index == 0
        assert s.status == SessionStatus.STARTED

    async def test_status_enum_values(self, db):
        for status in SessionStatus:
            assert isinstance(status.value, str)


class TestSessionSchemas:
    def test_create_requires_test_id(self):
        with pytest.raises(Exception):
            SessionCreate()

    def test_create_optional_submission_id(self):
        s = SessionCreate(test_id=5)
        assert s.submission_id is None

    def test_create_with_submission_id(self):
        s = SessionCreate(test_id=5, submission_id=10)
        assert s.submission_id == 10
```

For the route handler, mock the httpx call with `respx` (add to `requirements-test.txt`):

```python
import respx
import httpx

MOCK_QUESTION = {
    "_id": "507f1f77bcf86cd799439011",
    "question_text": "What is Python?",
    "type": "mcq",
    "difficulty": "easy",
    "options": [{"option_id": 1, "text": "A language"}],
}

@respx.mock
async def test_create_session_returns_201(async_client, db, seeded_test):
    respx.get(re.compile(r".*/questions/sample.*")).mock(
        return_value=httpx.Response(200, json=[MOCK_QUESTION])
    )
    resp = await async_client.post(
        "/v1/api/sessions/",
        json={"test_id": seeded_test.id},
        headers={"X-User-Id": "1", "X-User-Role": "PARTICIPANT", "X-User-Email": "p@test.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert UUID(data["session_id"])
    assert "expires_at" in data
    assert data["first_question"]["question_id"] == MOCK_QUESTION["_id"]
    assert "correct_answers" not in data["first_question"]

@respx.mock
async def test_create_session_502_when_qms_down(async_client, seeded_test):
    respx.get(re.compile(r".*/questions/sample.*")).mock(
        return_value=httpx.Response(503)
    )
    resp = await async_client.post(
        "/v1/api/sessions/",
        json={"test_id": seeded_test.id},
        headers={"X-User-Id": "1", "X-User-Role": "PARTICIPANT", "X-User-Email": "p@test.com"},
    )
    assert resp.status_code == 502

async def test_create_session_404_unknown_test(async_client):
    resp = await async_client.post(
        "/v1/api/sessions/",
        json={"test_id": 99999},
        headers={"X-User-Id": "1", "X-User-Role": "PARTICIPANT", "X-User-Email": "p@test.com"},
    )
    assert resp.status_code == 404
```

---

## Files Changed

| Action | Path |
|--------|------|
| Create | `services/test-management-service/migrations/` (Alembic init) |
| Create | `services/test-management-service/src/models/quiz_session.py` |
| Create | `services/test-management-service/src/schemas/quiz_session_schema.py` |
| Create | `services/test-management-service/src/v1/routes/quiz_session_route.py` |
| Create | `services/test-management-service/src/utils/http_client.py` |
| Create | `services/test-management-service/tests/test_quiz_session.py` |
| Modify | `services/test-management-service/src/db/session.py` (import quiz_session in init_db) |
| Modify | `services/test-management-service/src/config/settings.py` (add QUESTION_SERVICE_URL) |
| Modify | `services/test-management-service/main.py` (register quiz_session_router) |
| Modify | `services/question-management-service/src/services/question_service.py` (add sample_questions) |
| Modify | `services/question-management-service/src/v1/routes/question_routes.py` (add /sample route) |
| Modify | `services/api-gateway-service/main.py` (add /sessions pattern to ROUTES) |
| Modify | `services/test-management-service/requirements-test.txt` (add respx) |

---

## Verification

```bash
# 1. Alembic at head
alembic current
# → 0004_add_quiz_sessions (head)

# 2. Sample endpoint works
curl "http://localhost:8003/v1/api/questions/sample?n=3"
# → JSON array of 3 question documents

# 3. Session creation (requires running Compose stack + seeded data)
TOKEN=$(curl -s -X POST http://localhost:8000/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"participant@test.com","password":"test123"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/v1/api/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_id": 1}' | jq .
# → 201: session_id (UUID), session_token, server_now, expires_at, first_question
# → first_question must NOT contain correct_answers

# 4. Unit tests pass
cd services/test-management-service
pytest tests/test_quiz_session.py -v
```
