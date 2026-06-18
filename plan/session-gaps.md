# Session Gaps — Implementation Plan

## What this addresses

Three architectural gaps identified in code review of the Day 11 session creation feature:

1. **Expiry + idempotency** — expired sessions were never marked EXPIRED; `POST /sessions` on an expired session returned a dead token with no path to start fresh.
2. **Question position** — `TestSession` had no ordered question list or position tracker; W3-F2's answer endpoint would have had nowhere to read from or write to.
3. **Randomisation** — `by-skill?limit=1` returned the same first MongoDB document for every participant; no `$sample` support existed.

---

## Changes made

### question-management-service

| File | Change |
|---|---|
| `src/repositories/question_repository.py` | Added `sample(count, skill)` — runs `$match` + `$sample` aggregation pipeline |
| `src/services/question_service.py` | Added `sample_questions(count, skill)` delegating to repository |
| `src/v1/routes/question_routes.py` | Added `GET /v1/api/questions/sample?count=N&skill=X` — placed **before** `/{id}` to avoid FastAPI treating "sample" as an ID |

### test-management-service

| File | Change |
|---|---|
| `src/models/session_question.py` | **New** — `session_questions` table: `session_id` (FK), `position`, `question_id` (MongoDB ObjectId as String(24)); unique on (session_id, position) |
| `src/models/test_session.py` | Added `current_position` (Integer, default=0) column |
| `src/repositories/session_question_repository.py` | **New** — `bulk_create`, `list_by_session`, `get_by_position` |
| `src/db/session.py` | Added `SessionQuestion` import in `init_db()` so `create_all` creates the table |
| `src/schemas/session_schema.py` | Added `total_questions: int` and `current_position: int` to `SessionResponse` |
| `src/services/session_service.py` | Full rewrite — see logic below |

---

## Session service logic (new flow)

```
POST /sessions
  │
  ├─ validate quiz (exists, QUIZ type, active)
  ├─ find submission (404 if none, 409 if terminal status)
  │
  ├─ idempotency check:
  │   ├─ existing ACTIVE + not expired → return existing session (re-fetch first question)
  │   └─ existing ACTIVE + expired    → mark EXPIRED, fall through to create new
  │
  ├─ mint UUID token, compute server_now + expires_at (server-side only)
  │
  ├─ call /v1/api/questions/sample?count=N&skill=X  (graceful degradation → [])
  │
  ├─ db.add(TestSession) + db.flush() → get session.id
  ├─ SessionQuestionRepository.bulk_create(session.id, question_ids)  ← single transaction
  ├─ db.commit()
  │
  ├─ update submission → IN_PROGRESS (if ASSIGNED)
  │
  └─ return SessionResponse {
       session_token, submission_id, test_id,
       server_now, expires_at,
       total_questions,     ← new: lets frontend show "Q 1 of 20"
       current_position,    ← new: always 0 on creation
       first_question       ← QuestionOut (None if question-service degraded)
     }
```

---

## What W3-F2's answer endpoint needs

The `session_questions` table is the source of truth for question order. The answer endpoint should:

1. Load `TestSession` by token — verify ACTIVE + not expired
2. Read `SessionQuestionRepository.get_by_position(session_id, current_position)` → current `question_id`
3. Validate the submitted answer against question-service
4. Increment `TestSession.current_position`
5. If `current_position == total_questions` → mark session COMPLETED, update submission to COMPLETED
6. Return next question via `get_by_position(session_id, new_position)`

---

## Verification

```bash
# 1. Confirm tables created
psql -U root -d eval_ai_dev -c "\dt session_questions"
psql -U root -d eval_ai_dev -c "\d test_sessions"  # check current_position column

# 2. Confirm /sample returns different results per call (randomness)
curl "http://localhost:8003/v1/api/questions/sample?count=5&skill=Python" | jq '.[].id'
curl "http://localhost:8003/v1/api/questions/sample?count=5&skill=Python" | jq '.[].id'
# IDs should differ between calls

# 3. Create session — check total_questions and current_position in response
curl -X POST http://localhost:8000/v1/api/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"quiz_id": 1}' | jq '{total_questions, current_position, first_question: .first_question.id}'

# 4. Idempotency — second call returns same session_token
curl -X POST http://localhost:8000/v1/api/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"quiz_id": 1}' | jq '.session_token'
# Must match first call

# 5. Expiry — manually set expires_at in past, call again
psql -U root -d eval_ai_dev -c \
  "UPDATE test_sessions SET expires_at = NOW() - INTERVAL '1 hour' WHERE id = 1;"
curl -X POST http://localhost:8000/v1/api/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"quiz_id": 1}' | jq '.session_token'
# Must be a NEW different token
```
