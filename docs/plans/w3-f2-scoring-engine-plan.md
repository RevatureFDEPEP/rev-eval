# W3-F2 Implementation Plan — Scoring Engine + Answer Submission

**Status:** ❌ Not Started  
**Tracker:** `docs/feature_specs/w3-f2-scoring-engine-locking.md`  
**Spec:** `docs/feature_specs/w3-f2-scoring-engine-locking.md`  
**Branch:** `tianyac-scoring-engine`  
**Updated:** 2026-06-17

---

## Goal

Add deterministic scoring functions and a `POST /v1/api/sessions/{id}/answer` endpoint to test-management-service that:
1. Locks the session row pessimistically before reading `current_index`
2. Fetches `correct_answers` from QMS (service-to-service)
3. Scores with exact-match (MCQ/TRUE_FALSE) or Jaccard partial-credit (MULTI)
4. Advances `current_index`; transitions session to SUBMITTED on last question
5. Deduplicates retried requests via `Idempotency-Key` header

---

## Baseline Gaps

| Gap | Detail |
|-----|--------|
| No scoring logic | No answer comparison anywhere in the service |
| No answer endpoint | `quiz_session_route.py` only has `POST /sessions` (create) |
| No answer storage | No `session_answers` table |
| No idempotency | No dedup table, no `Idempotency-Key` handling |
| QMS `correct_answers` not fetched | `http_client.py` has only `get_qms_client()`; no per-question fetch |

---

## New Files

### `src/scoring/exact_match.py`
Pure function, no DB, no side effects.
```python
def score_exact(correct: list, submitted: list) -> float:
    # Normalise to str, compare as sets → 1.0 or 0.0
```
Edge cases: both empty → 1.0; submitted empty → 0.0.

### `src/scoring/partial_credit.py`
Pure function. Jaccard: `|intersection| / |union|` on normalised sets.
```python
def score_jaccard(correct: list, submitted: list) -> float:
    # Returns 0.0 when union is empty
```
Extra wrong answers in submitted increase union → lower score (correct by definition).

### `src/scoring/__init__.py`
Dispatcher + `ScoreResult` dataclass.
```python
@dataclass
class ScoreResult:
    score: Optional[float]   # None for TEXT / missing correct_answers
    algorithm: str           # "exact_match" | "jaccard" | "none"

def score_question(question_type, correct_answers, submitted_answers) -> ScoreResult:
    # "mcq" / "true_false" → exact_match
    # "multi"              → jaccard
    # "text" / other       → ScoreResult(None, "none")
    # correct_answers None/empty → ScoreResult(None, "none") regardless of type
```

### `src/models/session_answer.py`
```python
class SessionAnswer(Base):
    __tablename__ = "session_answers"
    id                = Column(Integer, primary_key=True, index=True)
    session_id        = Column(String(36), ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    question_id       = Column(String(64), nullable=False)
    question_index    = Column(Integer, nullable=False)
    question_type     = Column(String(32), nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    correct_answers   = Column(JSON, nullable=True)   # stored for audit; NULL for TEXT
    score             = Column(Float, nullable=True)  # NULL for TEXT
    created_at        = Column(DateTime, default=datetime.utcnow)
```
Immutable — no `updated_at`.

### `src/models/idempotency_key.py`
```python
class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id            = Column(Integer, primary_key=True, index=True)
    key           = Column(String(128), unique=True, nullable=False, index=True)
    session_id    = Column(String(36), ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    response_body = Column(JSON, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
```
`key` unique constraint is the concurrent-write guard. `session_id` prevents cross-session replay.

### `migrations/versions/0007_add_session_answers_and_idempotency.py`
`down_revision = "0006"`. Creates both tables with indexes. `downgrade()` drops in reverse order.  
*(0006 is already taken by `replace_test_categories_with_skill_categories`)*

### `tests/test_scoring.py`
Pure-function tests — no `db` fixture, no async.

| Class | Parametrized cases |
|---|---|
| `TestExactMatch` | MCQ correct/wrong, TRUE_FALSE correct/wrong, empty submitted |
| `TestJaccard` | full match→1.0, partial→≈0.333, zero overlap→0.0, extra wrong→0.5, empty→0.0 |
| `TestScoreDispatcher` | mcq/true_false→exact, multi→jaccard, text→None, None correct_answers→None |

### `tests/test_answer_endpoint.py`
Uses `db` fixture; patches `fetch_question` via `AsyncMock`.

| Test | Assertion |
|---|---|
| Normal flow (not last question) | 200, score returned, next_question present, current_index advances |
| Last question | session→SUBMITTED, submission.status→COMPLETED, ai_score set, next_question=None |
| Already-SUBMITTED session | 409 |
| Wrong question_id | 422 |
| Duplicate idempotency key | 200 cached response, no new SessionAnswer row |
| TEXT question | score=null, index still advances |

---

## Modified Files

### `src/utils/http_client.py`
Add after existing `get_qms_client()`:
```python
async def fetch_question(question_id: str, correlation_id: str = "") -> dict:
    """Service-to-service fetch including correct_answers (never forwarded to client)."""
    client = get_qms_client()
    try:
        resp = await client.get(
            f"/v1/api/questions/{question_id}",
            headers={"X-Correlation-Id": correlation_id} if correlation_id else {},
        )
    except Exception as exc:
        raise HTTPException(502, detail=f"Question service error: {exc}") from exc
    if resp.status_code == 404:
        raise HTTPException(404, detail=f"Question {question_id} not found")
    resp.raise_for_status()
    return resp.json()
```

### `src/schemas/quiz_session_schema.py`
Append:
```python
class AnswerSubmit(BaseModel):
    question_id: str
    submitted_answers: List[Union[int, bool, str]]

class AnswerResponse(BaseModel):
    session_id: str
    question_id: str
    question_index: int           # 0-based index of answered question
    score: Optional[float]        # None for TEXT questions
    algorithm: str                # "exact_match" | "jaccard" | "none"
    session_status: str
    current_index: int            # new position after advance
    next_question: Optional[QuizQuestionOut]  # None when session just submitted
```

### `src/v1/routes/quiz_session_route.py`
Add `POST /sessions/{session_id}/answer`. Full flow inside one `async with db.begin()`:

```
1.  Read Idempotency-Key header (optional, max 128 chars)
2.  If key present → SELECT idempotency_keys WHERE key=… AND session_id=…
      If found → return JSONResponse(row.response_body, 200)   [early exit]
3.  SELECT quiz_sessions WHERE id=session_id WITH FOR UPDATE
4.  404 if not found
5.  409 if status == SUBMITTED or EXPIRED
6.  422 if body.question_id != session.question_ids[session.current_index]
7.  qms = await fetch_question(body.question_id, correlation_id)
8.  result = score_question(qms["type"], qms.get("correct_answers"), body.submitted_answers)
9.  db.add(SessionAnswer(session_id, question_id, current_index, question_type=qms["type"],
           submitted_answers, correct_answers=qms.get("correct_answers"), score=result.score))
10. answered_index = session.current_index
    new_index = answered_index + 1
    is_last = new_index >= len(session.question_ids)
    session.current_index = new_index
    session.status = SUBMITTED if is_last else IN_PROGRESS
    if is_last: session.submitted_at = datetime.utcnow()
11. If is_last and session.submission_id:
      SELECT test_submissions WHERE id=session.submission_id WITH FOR UPDATE
      SELECT all session_answers WHERE session_id=…  (includes just-added row via identity map)
      scores = [a.score for a in answers if a.score is not None]
      sub.ai_score = round(mean(scores) * 100) if scores else None
      sub.status = COMPLETED; sub.submitted_at = session.submitted_at
12. next_question: if not is_last, fetch qms for session.question_ids[new_index] → map to QuizQuestionOut
13. Build AnswerResponse → response_body dict
14. If key present:
      try: db.add(IdempotencyKey(key, session_id, response_body))
      except IntegrityError: pass   (concurrent duplicate — response already computed)
15. Transaction auto-commits at end of context
16. return AnswerResponse(…)
```

**SELECT FOR UPDATE note**: `.with_for_update()` compiles to `FOR UPDATE` on Postgres and is silently ignored by aiosqlite in tests — no conditional branching needed.

### `tests/conftest.py`
Add two lines after existing model imports (after line 26):
```python
from src.models.session_answer import SessionAnswer    # noqa: F401
from src.models.idempotency_key import IdempotencyKey  # noqa: F401
```

### `migrations/env.py`
Add alongside existing model imports:
```python
import src.models.session_answer   # noqa: F401, E402
import src.models.idempotency_key  # noqa: F401, E402
```

---

## Implementation Order

1. `src/scoring/exact_match.py`
2. `src/scoring/partial_credit.py`
3. `src/scoring/__init__.py`
4. `src/models/session_answer.py`
5. `src/models/idempotency_key.py`
6. `tests/conftest.py` — add model imports (needed before endpoint tests run)
7. `src/schemas/quiz_session_schema.py` — add AnswerSubmit, AnswerResponse
8. `src/utils/http_client.py` — add fetch_question
9. `src/v1/routes/quiz_session_route.py` — add answer endpoint
10. `migrations/env.py`
11. `migrations/versions/0007_add_session_answers_and_idempotency.py`
12. `tests/test_scoring.py`
13. `tests/test_answer_endpoint.py`

---

## Verification

```bash
cd services/test-management-service
source .venv/bin/activate

# Lint
ruff check src/ tests/

# Scoring unit tests
pytest tests/test_scoring.py -v

# Endpoint integration tests
pytest tests/test_answer_endpoint.py -v

# Full suite
pytest --tb=short

# Apply migration (real Postgres)
alembic upgrade head
alembic current   # should show 0007
```
