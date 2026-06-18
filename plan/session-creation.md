# Session Creation Backend — Day 11

## Context

The platform currently has Tests and TestSubmissions, but no concept of an active test-taking session. When a participant starts a quiz, there is no server-side record of *when* it started, *when* it expires, or *which question* is currently displayed. This feature adds a `TestSession` row minted by the server (UUID token, server_now, expires_at), transitions the submission to IN_PROGRESS, and calls question-management-service to pre-fetch the first question — establishing the cross-service HTTP call pattern (timeout, retries, correlation ID).

---

## New Files (6)

| File | Purpose |
|---|---|
| `src/models/test_session.py` | SQLAlchemy model — `test_sessions` table |
| `src/schemas/session_schema.py` | `SessionCreateRequest`, `QuestionOut`, `SessionResponse` |
| `src/utils/http_client.py` | Reusable httpx helper: timeout, 3-attempt backoff retry, X-Correlation-Id |
| `src/repositories/session_repository.py` | `create`, `get_by_token`, `get_by_submission_id` |
| `src/services/session_service.py` | Core orchestration logic |
| `src/v1/routes/session_route.py` | `POST /sessions/` — PARTICIPANT only |

All paths are under `services/test-management-service/`.

---

## Modified Files (5)

| File | Change |
|---|---|
| `src/config/settings.py` | Add `QUESTION_SERVICE_URL: str = "http://localhost:8003"` |
| `src/db/session.py` → `init_db()` | Import `TestSession` so `create_all` creates the table |
| `main.py` | `include_router(session_router, prefix="/v1/api")` |
| `services/api-gateway-service/main.py` | Add `{"pattern": r"^/v1/api/sessions(/.*)?$", "service": "test-management-service"}` to `ROUTES` |
| `docker-compose.yml` | Add `QUESTION_SERVICE_URL: http://question-management-service:8003` to `test-management-service.environment` |

---

## Model: `test_sessions`

```python
class TestSession(Base):
    __tablename__ = "test_sessions"
    id           = Column(Integer, primary_key=True, index=True)
    token        = Column(String(36), unique=True, nullable=False, index=True)   # UUID4
    submission_id= Column(Integer, ForeignKey("test_submissions.id"), nullable=False, index=True)
    test_id      = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id      = Column(Integer, nullable=False)
    first_question_id = Column(String(24), nullable=True)                         # MongoDB ObjectId
    server_now   = Column(DateTime, nullable=False)                               # set server-side only
    expires_at   = Column(DateTime, nullable=False)                               # server_now + duration
    created_at   = Column(DateTime, default=datetime.utcnow)
```

No `relationship()` back-populate on TestSubmission — FK is enough for this feature.

`expires_at` fallback: `server_now + test.duration` if set, else `server_now + timedelta(hours=1)`.

---

## HTTP Client Utility (`src/utils/http_client.py`)

```python
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
MAX_ATTEMPTS = 3
RETRY_STATUSES = {502, 503, 504}

async def call_service(url, method="GET", *, correlation_id, json=None, timeout=None, max_attempts=MAX_ATTEMPTS):
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout or DEFAULT_TIMEOUT) as client:
                resp = await client.request(method, url, json=json,
                                            headers={"X-Correlation-Id": correlation_id})
            if resp.status_code not in RETRY_STATUSES:
                return resp
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        if attempt < max_attempts - 1:
            await asyncio.sleep(0.5 * (2 ** attempt))   # 0.5s, 1.0s
    raise httpx.ConnectError(f"Service unavailable after {max_attempts} attempts: {url}")
```

Retries on: `ConnectError`, `TimeoutException`, HTTP 502/503/504.  
Does NOT retry: 400/404/422/500 (deterministic upstream errors).

---

## Session Service Logic (`create_session`)

1. `TestRepository.get_by_id(db, quiz_id)` — 404 if missing, 400 if `test_type != QUIZ` or `active=False`
2. `TestSubmissionRepository.get_by_user_and_test(db, user_id, quiz_id)` — 404 if no submission, 409 if status is COMPLETED/EVALUATED/GRADED/ABANDONED
3. Mint `token = str(uuid.uuid4())`, `server_now = datetime.utcnow()`, compute `expires_at`
4. `SessionRepository.create(db, TestSession(...))` — write to Postgres before calling question-service
5. If `submission.status == ASSIGNED`: update to `IN_PROGRESS`, set `started_at = server_now`
6. Fetch first question via `call_service()`:
   - Get skills via `TestSkillRepository.list_by_test` → `SkillRepository.get_by_id`
   - URL: `.../v1/api/questions/by-skill/{skill_name}?limit=1` (or `.../filter?limit=1` if no skills)
   - On success: patch `session.first_question_id`, build `QuestionOut` (strips `correct_answers`, `sample_answer`, `answer_explanation`)
   - On failure after retries: `logger.warning(...)`, `first_question = None` (graceful degradation — session still created)
7. Return `SessionResponse`

---

## Schemas

**`SessionCreateRequest`:** `quiz_id: int`

**`QuestionOut`:** `id, type, question_text, options, difficulty, skills, tags` — intentionally excludes `correct_answers`, `sample_answer`, `answer_explanation`

**`SessionResponse`:** `session_token, submission_id, test_id, server_now, expires_at, first_question: QuestionOut | None`

---

## Route

```python
@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_participant),   # reuse existing dep
    db: AsyncSession = Depends(get_db),
):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    ...
```

Uses existing `get_current_participant` from `src/utils/dependencies.py` — enforces PARTICIPANT role.

---

## Error Map

| Condition | Status |
|---|---|
| Quiz not found | 404 |
| Test is INTERVIEW type or inactive | 400 |
| No submission for user+quiz | 404 |
| Submission in terminal status | 409 |
| Caller is TRAINER | 403 |
| question-service down (after retries) | 201 with `first_question: null` |

---

## Verification

```bash
# 1. Check table was created
psql -U root -d eval_ai_dev -c "\dt test_sessions"

# 2. Happy path (requires seeded PARTICIPANT + ASSIGNED submission)
curl -X POST http://localhost:8000/v1/api/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Correlation-Id: test-001" \
  -d '{"quiz_id": 1}'
# Expect: 201, session_token UUID, expires_at > server_now, first_question populated

# 3. Submission moves to IN_PROGRESS
curl http://localhost:8000/v1/api/submissions/1/ -H "Authorization: Bearer $TOKEN" | jq '.status'
# Expect: "IN_PROGRESS"

# 4. question-service degradation
docker compose stop question-management-service
curl -X POST http://localhost:8000/v1/api/sessions/ -H "Authorization: Bearer $TOKEN" -d '{"quiz_id": 2}'
# Expect: 201 with first_question: null; logs show 3 retry attempts

# 5. Error paths
curl -X POST .../sessions/ -d '{"quiz_id": 9999}'   # → 404
curl -X POST .../sessions/ (TRAINER token)           # → 403
```
