# W3-F2 — Scoring Engine with Exact-Match & Partial-Credit + Attempt Locking

**Status:** ✅ Completed
**Spec:** `days_11_15_features.md` §2 (Day 12)
**Depends on:** W3-F1 (sessions table, `session_id`, `current_index` must exist before the answer endpoint can lock and advance them), [W2-F2](w2-f2-unit-test-scaffolding.md) (pytest must be configured in test-management-service for the parameterized scoring tests to run in CI)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `PATCH /sessions/{id}/draft` + the session state machine established here are the base layer), W4-F1 (Results Reporting — sessions/answers must hold scored data), W4-F3 (Role-Based Aggregate Queries — answers data for `GROUP BY`/window functions), W4-F5 (Tech Debt Audit — scoring algorithm choice is one required ADR)
**Last updated:** 2026-06-17

Scoring logic + attempt-locking for quiz sessions.

## Steps

- [x] **1. Pure scoring module** — `score_answer(question, response)` supporting
      exact-match (MCQ/TRUE_FALSE) and partial-credit (MULTI).
- [x] **2. POST /sessions/{id}/answer + pessimistic lock** — `SELECT FOR UPDATE`
      on the session row; validate `current_index`, apply score, advance index.
- [x] **3. Idempotency** — re-submitting the same index returns the cached score
      without re-locking.
- [x] **4. State machine + finalization** — session transitions
      `active → submitted` when all questions answered; `score_total` computed.
- [x] **5. Parameterized pytest** — test every score branch (exact, partial, zero,
      boundary) using the in-memory DB fixture from [W2-F2](w2-f2-unit-test-scaffolding.md).

## Evidence

- **Branch:** `tianyac-scoring-engine` → merged PR #148
- **Commit:** `5fc9c05` — `feat(w3-f2): scoring engine + answer submission endpoint`
- **Scoring module:**
  - `services/test-management-service/src/scoring/exact_match.py` — exact-match (MCQ/TRUE_FALSE)
  - `services/test-management-service/src/scoring/partial_credit.py` — Jaccard partial-credit (MULTI)
  - `services/test-management-service/src/scoring/__init__.py` — `ScoreResult` dataclass + dispatcher
- **Models:**
  - `services/test-management-service/src/models/session_answer.py` — immutable answer record
  - `services/test-management-service/src/models/idempotency_key.py` — dedup table
- **Migration:** `services/test-management-service/migrations/versions/0007_add_session_answers_and_idempotency.py` — Alembic head at `0007`
- **Endpoint:** `services/test-management-service/src/v1/routes/quiz_session_route.py` — 16-step `POST /v1/api/sessions/{id}/answer` with `begin_nested` SAVEPOINT for concurrent idempotency-key dedup
- **HTTP client:** `services/test-management-service/src/utils/http_client.py` — `fetch_question()` for service-to-service QMS call
- **Schemas:** `services/test-management-service/src/schemas/quiz_session_schema.py` — `AnswerSubmit`, `AnswerResponse`
- **Tests:** 22 parameterized pure-function tests (`tests/test_scoring.py`) + 6 httpx integration tests (`tests/test_answer_endpoint.py`); 161 total passing
- **Plan:** `docs/plans/w3-f2-scoring-engine-plan.md`

## Remaining

Nothing. All acceptance criteria met.
