# Plan: Quiz Answer Submission with Scoring

## Context

The quiz session was built to create a session and return the first question, but has no way to accept answers, advance through the question list, or finalize a submission. This plan adds the full answer loop: pure scoring functions, a transactionally-safe answer endpoint with idempotency, and pytest coverage.

---

## 1. Scoring Module — `src/scoring/`

Create three files:

**`src/scoring/__init__.py`** — exports `ScoreResult`:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ScoreResult:
    earned: float
    max_points: float
    is_correct: bool
```

**`src/scoring/exact_match.py`** — single-select:
```python
def score_question(question_type, correct_answers, submitted_answers, max_points=1.0) -> ScoreResult:
    correct = set(correct_answers)
    submitted = set(submitted_answers)
    is_correct = correct == submitted
    return ScoreResult(earned=max_points if is_correct else 0.0, max_points=max_points, is_correct=is_correct)
```

**`src/scoring/partial_credit.py`** — multi-select, set-overlap with penalty:
```python
def score_question(question_type, correct_answers, submitted_answers, max_points=1.0) -> ScoreResult:
    correct = set(correct_answers)
    submitted = set(submitted_answers)
    hits = len(correct & submitted)
    false_positives = len(submitted - correct)
    ratio = max(0.0, hits - false_positives) / len(correct) if correct else 0.0
    earned = round(ratio * max_points, 4)
    return ScoreResult(earned=earned, max_points=max_points, is_correct=ratio == 1.0)
```

Both functions are pure (no I/O, no side effects). The caller selects which function based on `question_type`.

---

## 2. DB Schema Changes

### 2a. Update `Session` model — `src/models/session.py`

Add two columns:
- `question_ids = Column(JSON, nullable=False, default=list)` — ordered list of question ID strings sampled at session creation
- `submitted_at = Column(DateTime, nullable=True)` — set when session reaches COMPLETED

### 2b. New `SessionAnswer` model — `src/models/session_answer.py`

```
Table: session_answers
  id              Integer PK (autoincrement)
  session_id      UUID FK → sessions.session_id (CASCADE DELETE)
  question_id     String(64)   — MongoDB ObjectId string
  question_index  Integer      — position in question_ids list
  submitted_answers JSON       — list[str] submitted by participant
  earned_points   Float
  max_points      Float
  is_correct      Boolean
  answered_at     DateTime (default utcnow)
  UNIQUE (session_id, question_index)
```

### 2c. New `IdempotencyKey` model — `src/models/idempotency_key.py`

```
Table: idempotency_keys
  key             String(128) PK  — value from Idempotency-Key header
  session_id      UUID (indexed)
  response_json   JSON            — full serialized response dict
  created_at      DateTime (default utcnow)
```

### 2d. Alembic migration — `alembic/versions/c3d4e5f6a7b8_add_answer_tracking.py`

- `ALTER TABLE sessions ADD COLUMN question_ids JSON`
- `ALTER TABLE sessions ADD COLUMN submitted_at TIMESTAMP`
- `CREATE TABLE session_answers (...)`
- `CREATE TABLE idempotency_keys (...)`

Also update `init_db()` in `src/db/session.py` to import the two new models.

---

## 3. Update Session Creation to Persist `question_ids`

In `src/services/session_service.py`, after sampling `question_ids` from question-management, add `question_ids=question_ids` when constructing the `Session` ORM object (line ~80). This is the only change to the existing service.

---

## 4. New Schemas — `src/schemas/session_schema.py`

Append:
```python
class AnswerSubmit(BaseModel):
    question_id: str
    submitted_answers: list[str]

class AnswerResponse(BaseModel):
    question_id: str
    earned_points: float
    max_points: float
    is_correct: bool
    next_question: dict[str, Any] | None   # None when session is now COMPLETED
    session_status: str
    current_index: int
```

---

## 5. New Repositories

**`src/repositories/session_repository.py`** — add method:
```python
@staticmethod
async def get_by_id_for_update(db: AsyncSession, session_id: UUID) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.session_id == session_id).with_for_update()
    )
    return result.scalar_one_or_none()
```

**`src/repositories/session_answer_repository.py`** — new file with `create()` and `list_by_session()`.

**`src/repositories/idempotency_repository.py`** — new file with `get_by_key()` and `create()`.

---

## 6. Answer Submission Service — `src/services/session_service.py`

Add `SessionService.submit_answer()` as a static async method. Full logic:

```
1. If Idempotency-Key header present: check idempotency_keys table.
   On hit → return cached AnswerResponse immediately (no re-scoring).

2. Open explicit transaction (db.begin() already active via FastAPI dependency).
   SELECT ... FOR UPDATE on sessions where session_id = {id}.

3. If session not found → 404.
   If session.status != ACTIVE → 409 ("Session is already completed or expired").
   If answer.question_id != session.question_ids[session.current_index] → 422.

4. Fetch question body from question-management-service to get:
   - correct_answers: list[str]
   - question_type: "SINGLE_SELECT" | "MULTI_SELECT"

5. Dispatch to scorer:
   - SINGLE_SELECT → exact_match.score_question(...)
   - MULTI_SELECT  → partial_credit.score_question(...)

6. Persist SessionAnswer row.

7. Advance session.current_index += 1.
   If session.current_index == len(session.question_ids):
     session.status = SessionStatus.COMPLETED
     session.submitted_at = datetime.utcnow()
     next_question = None
   Else:
     next_question_id = session.question_ids[session.current_index]
     next_question = await fetch question from question-management

8. Commit.

9. If Idempotency-Key present: persist idempotency_keys row (within same transaction before commit).

10. Return AnswerResponse.
```

---

## 7. Route — `src/v1/routes/session_route.py`

Add endpoint:
```python
@router.post("/{session_id}/answers", response_model=AnswerResponse, status_code=200)
async def submit_answer(
    session_id: UUID,
    answer_in: AnswerSubmit,
    current_user: dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    return await SessionService.submit_answer(
        db, session_id, answer_in, int(current_user["id"]),
        http_client, idempotency_key, x_correlation_id
    )
```

---

## 8. Tests — `tests/test_scoring.py`

Pure unit tests, no DB fixture required. Use `pytest.mark.parametrize` with a matrix covering four named scenarios:

**Exact-match** (single-select, via `exact_match.score_question`):

| Scenario | correct | submitted | earned | is_correct |
|---|---|---|---|---|
| correct answer selected | ["A"] | ["A"] | 1.0 | True |
| wrong answer selected | ["A"] | ["B"] | 0.0 | False |
| no answer submitted | ["A"] | [] | 0.0 | False |

**Full-match** (multi-select, all correct + no false positives, via `partial_credit.score_question`):

| Scenario | correct | submitted | earned | is_correct |
|---|---|---|---|---|
| all 2 correct, 0 FP | ["A","B"] | ["A","B"] | 1.0 | True |
| all 3 correct, 0 FP | ["A","B","C"] | ["A","B","C"] | 1.0 | True |

**Partial-credit** (multi-select, some correct, zero false positives — tests set-overlap numerator):

| Scenario | correct | submitted | earned | is_correct |
|---|---|---|---|---|
| 1/2 correct, 0 FP | ["A","B"] | ["A"] | 0.5 | False |
| 2/3 correct, 0 FP | ["A","B","C"] | ["A","B"] | 0.6667 | False |
| 0 correct (none submitted) | ["A","B"] | [] | 0.0 | False |

**Jaccard / penalty** (multi-select, false positives reduce or zero out the score — tests the penalty subtraction):

| Scenario | correct | submitted | earned | is_correct |
|---|---|---|---|---|
| 2/3 correct, 1 FP → net 1/3 | ["A","B","C"] | ["A","B","D"] | 0.3333 | False (hits=2, FP=1 → max(0,1)/3) |
| 1/2 correct, 1 FP → net 0 | ["A","B"] | ["A","C"] | 0.0 | False (hits=1, FP=1 → max(0,0)/2) |
| 0 correct, all FP | ["A","B"] | ["C","D"] | 0.0 | False |
| 1 correct, 1 FP over-selected | ["A"] | ["A","B"] | 0.0 | False (hits=1, FP=1 → max(0,0)/1) |

Also test `ScoreResult` immutability (frozen dataclass raises on attribute assignment).

---

## File Change Summary

| File | Action |
|---|---|
| `src/scoring/__init__.py` | Create |
| `src/scoring/exact_match.py` | Create |
| `src/scoring/partial_credit.py` | Create |
| `src/models/session.py` | Edit — add `question_ids`, `submitted_at` |
| `src/models/session_answer.py` | Create |
| `src/models/idempotency_key.py` | Create |
| `src/db/session.py` | Edit — import new models in `init_db()` |
| `src/schemas/session_schema.py` | Edit — add `AnswerSubmit`, `AnswerResponse` |
| `src/repositories/session_repository.py` | Edit — add `get_by_id_for_update()` |
| `src/repositories/session_answer_repository.py` | Create |
| `src/repositories/idempotency_repository.py` | Create |
| `src/services/session_service.py` | Edit — persist `question_ids`, add `submit_answer()` |
| `src/v1/routes/session_route.py` | Edit — add `POST /{session_id}/answers` |
| `alembic/versions/c3d4e5f6a7b8_add_answer_tracking.py` | Create |
| `tests/test_scoring.py` | Create |

---

## Verification

```bash
# Run scoring tests (pure, no DB needed)
pytest tests/test_scoring.py -v

# Run all tests
pytest tests/ -v

# Manual smoke test (requires full stack running):
# 1. POST /v1/api/sessions/  → get session_id + first_question
# 2. POST /v1/api/sessions/{id}/answers  with question_id + submitted_answers
#    → confirm earned_points, next_question returned
# 3. Repeat until all questions answered
#    → confirm session_status == "COMPLETED", next_question == null
# 4. POST again → confirm 409 returned
# 5. Replay step 2 with same Idempotency-Key → confirm identical response, no re-score
```
