# Plan: POST /sessions — Test Session Bootstrap

## Context

Test-management-service currently has no concept of an active test session. When a participant starts a test, the client has no server-authoritative record of when the test began, when it expires, or which questions were selected. This plan adds a `sessions` table, an Alembic migration, and a `POST /v1/api/sessions` endpoint that:
- issues server-computed timing (never trusts the client for `expires_at`)
- samples questions from question-management-service via MongoDB `$sample`
- returns the first question body in the same response
- propagates `X-Correlation-Id` across all inter-service calls

---

## Files Changed

### question-management-service (new endpoint)

**`services/question-management-service/src/schemas/question.py`** — add two models:
```python
class QuestionSampleRequest(BaseModel):
    skills: list[str]
    count: int = Field(..., ge=1, le=500)

class QuestionSampleResponse(BaseModel):
    question_ids: list[str]
```

**`services/question-management-service/src/repositories/question_repository.py`** — add method:
```python
@staticmethod
async def sample_ids_by_skills(skills: list[str], count: int) -> list[str]:
    collection = Question.get_motor_collection()
    pipeline = [
        {"$match": {"skills": {"$in": skills}}},
        {"$sample": {"size": count}},
        {"$project": {"_id": 1}},
    ]
    docs = await collection.aggregate(pipeline).to_list(length=count)
    return [str(doc["_id"]) for doc in docs]
```
Beanie has no `$sample` abstraction; Motor's raw `aggregate()` on `Question.get_motor_collection()` is the only path.

**`services/question-management-service/src/services/question_service.py`** — add:
```python
@staticmethod
async def sample_question_ids(skills: list[str], count: int) -> list[str]:
    return await QuestionRepository.sample_ids_by_skills(skills, count)
```

**`services/question-management-service/src/v1/routes/question_routes.py`** — add route **before** the `/{id}` catch-all (order matters):
```python
@router.post("/sample", response_model=QuestionSampleResponse, status_code=200)
async def sample_question_ids(body: QuestionSampleRequest):
    ids = await QuestionService.sample_question_ids(body.skills, body.count)
    return QuestionSampleResponse(question_ids=ids)
```

---

### test-management-service

**`services/test-management-service/src/config/settings.py`** — add:
```python
QUESTION_SERVICE_URL: str = "http://question-management-service:8003"
```

**`services/test-management-service/src/models/session.py`** — new file:
```python
import enum, uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base

class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"

class Session(Base):
    __tablename__ = "sessions"
    session_id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id       = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id       = Column(Integer, nullable=False, index=True)
    session_token = Column(String(64), nullable=False, unique=True)
    server_now    = Column(DateTime, nullable=False)
    expires_at    = Column(DateTime, nullable=False)
    status        = Column(Enum(SessionStatus, name="sessionstatus"), nullable=False, default=SessionStatus.ACTIVE)
    current_index = Column(Integer, nullable=False, default=0)
```
`String(64)` fits `secrets.token_hex(32)` exactly (64 hex chars). Naive `DateTime` matches the existing codebase's UTC-without-tzinfo pattern.

**`services/test-management-service/alembic/versions/b2c3d4e5f6a7_add_sessions_table.py`** — new migration:
```python
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"  # existing migration

def upgrade():
    op.create_table("sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("server_now", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE","COMPLETED","EXPIRED", name="sessionstatus"),
                  nullable=False, server_default="ACTIVE"),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index("ix_sessions_test_id", "sessions", ["test_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

def downgrade():
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_test_id", table_name="sessions")
    op.drop_table("sessions")
    op.execute("DROP TYPE IF EXISTS sessionstatus")  # must drop enum explicitly
```
`downgrade()` must explicitly drop the PostgreSQL ENUM type or a re-apply after rollback will fail with `type "sessionstatus" already exists`.

**`services/test-management-service/alembic/env.py`** — add after line 17 (after existing model imports):
```python
from src.models.session import Session  # noqa: E402, F401
```

**`services/test-management-service/src/db/session.py`** — add to `init_db()` import block (lines 45-49):
```python
from src.models.session import Session  # noqa: F401
```

**`services/test-management-service/src/schemas/session_schema.py`** — new file:
```python
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class SessionCreate(BaseModel):
    test_id: int

class SessionOut(BaseModel):
    session_id: uuid.UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: dict[str, Any]

    class Config:
        from_attributes = True
```

**`services/test-management-service/src/repositories/session_repository.py`** — new file, mirrors existing repo pattern:
```python
class SessionRepository:
    @staticmethod
    async def create(db: AsyncSession, session: Session) -> Session:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
```
Accepts a pre-built ORM instance (same pattern as `TestSubmissionRepository`).

**`services/test-management-service/src/utils/dependencies.py`** — add at end of file:
```python
async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client
```

**`services/test-management-service/src/services/session_service.py`** — new file, orchestration logic:

```
1. TestRepository.get_by_id(db, test_id)              → 404 if missing
2. TestSkillRepository.list_by_test(db, test_id)       → list[TestSkill]
   SkillRepository.get_by_id(db, link.skill_id)        → skill names list
3. session_id = uuid4(); session_token = secrets.token_hex(32)
   server_now = datetime.utcnow()
   expires_at = server_now + test.duration             # test.duration is timedelta (asyncpg returns timedelta for INTERVAL)
4. POST {QUESTION_SERVICE_URL}/v1/api/questions/sample
   body={"skills": skill_names, "count": test.number_of_questions}
   headers={"X-Correlation-Id": correlation_id} if present
   → question_ids: list[str]; raise 422 if empty
5. GET {QUESTION_SERVICE_URL}/v1/api/questions/{question_ids[0]}
   headers={"X-Correlation-Id": correlation_id} if present
   → first_question: dict
6. SessionRepository.create(db, Session(...))          # persist after both calls succeed
7. return SessionOut(...)
```

Error handling: `httpx.HTTPStatusError` → 502, `httpx.RequestError` → 503 (matches pattern in `test_submission_service.py`).

**`services/test-management-service/src/v1/routes/session_route.py`** — new file:
```python
router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("/", response_model=SessionOut, status_code=201)
async def create_session(
    session_in: SessionCreate,
    current_user: dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    return await SessionService.create_session(
        db, session_in, int(current_user["id"]), http_client, x_correlation_id
    )
```

**`services/test-management-service/main.py`** — three changes:
1. Add `import httpx` at top
2. Add `from src.v1.routes.session_route import router as session_router` and `app.include_router(session_router, prefix="/v1/api")`
3. Extend `on_startup` and add `on_shutdown`:
```python
@app.on_event("startup")
async def on_startup():
    await init_db()
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

@app.on_event("shutdown")
async def on_shutdown():
    await app.state.http_client.aclose()
```

---

## Implementation Order

1. question-management-service: schemas → repository → service → route
2. test-management-service `settings.py`
3. test-management-service `models/session.py`
4. Alembic migration file + `env.py` import + `db/session.py` import
5. `schemas/session_schema.py`
6. `repositories/session_repository.py`
7. `utils/dependencies.py` (`get_http_client`)
8. `services/session_service.py`
9. `v1/routes/session_route.py`
10. `main.py`

---

## Verification

```bash
# Run the migration
cd services/test-management-service
alembic upgrade head

# Start full stack
docker compose up --build

# Seed a test with skills
cd services/test-management-service && python seed_db.py

# Create a session (assumes gateway running, auth cookie set)
curl -X POST http://localhost:8000/v1/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: test-trace-001" \
  -b "auth_token=<jwt>" \
  -d '{"test_id": 1}'

# Expected response keys: session_id, session_token, server_now, expires_at, first_question
# Verify: expires_at - server_now == test.duration_seconds

# Run tests
cd services/test-management-service && pytest tests/ -v
cd services/question-management-service && pytest tests/ -v
```
