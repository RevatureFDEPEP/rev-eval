# W3-F2 — Scoring Engine with Exact-Match & Partial-Credit + Attempt Locking

**Status:** ✅ Completed
**Spec:** `days_11_15_features.md` §2 (Day 12)
**Depends on:** W3-F1 (sessions table, `session_id`, `current_index` must exist before the answer endpoint can lock and advance them), [W2-F2](w2-f2-unit-test-scaffolding.md) (pytest must be configured in test-management-service for the parameterized scoring tests to run in CI)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `PATCH /sessions/{id}/draft` + the session state machine established here are the base layer), W4-F1 (Results Reporting — sessions/answers must hold scored data), W4-F3 (Role-Based Aggregate Queries — answers data for `GROUP BY`/window functions), W4-F5 (Tech Debt Audit — scoring algorithm choice is one required ADR)
**Last updated:** 2026-06-08

Build pure, deterministic scoring functions for single-select (exact-match) and
multi-select (partial-credit) questions, then wire them into the answer
submission endpoint with pessimistic locking, idempotency, and state
finalization.

## Steps

- [x] **1. Pure scoring module** — `src/scoring/exact_match.py` (single-select,
      set equality) and `src/scoring/partial_credit.py` (multi-select, Jaccard),
      each exposing a pure `score_question(question_type, correct_answers,
      submitted_answers) -> ScoreResult` with **no DB access or side effects**.
      Shared `ScoreResult` in `src/scoring/result.py`; `src/scoring/__init__.py`
      `score(...)` dispatches by type. ADR rationale (Jaccard vs.
      all-or-nothing vs. correct-minus-wrong) in the `partial_credit` docstring.
- [x] **2. POST /sessions/{id}/answer + pessimistic lock** — single transaction
      in `SessionService.submit_answer`; `SessionRepository.get_for_update`
      issues `SELECT ... FOR UPDATE` (`with_for_update()`) on the session row
      **before** reading `current_index`, so concurrent retries serialize.
      Route at `src/v1/routes/session_route.py`.
- [x] **3. Idempotency** — `Idempotency-Key` header is **required** (422 if
      missing/blank). Dedup stored in the `idempotency_keys` table scoped to
      `(session_id, key)`; a retry replays the stored response body without
      re-scoring (`IdempotencyRepository`).
- [x] **4. State machine + finalization** — after scoring, `current_index` is
      advanced. On the final question `status` → `SUBMITTED` and `submitted_at`
      is recorded; further mutations return `409`. `SUBMITTED`/`EXPIRED` are
      terminal; an elapsed `expires_at` transitions the session to `EXPIRED`
      and returns `409`.
- [x] **5. Parameterized pytest** — `tests/test_scoring.py` (exact-match,
      full-match, Jaccard, partial-credit matrix; pure-function level) and
      `tests/test_answer_endpoint.py` (lock/idempotency/state/finalization/
      score-hidden, plus route-level 422). **89 passed, coverage 78%.**

## Evidence

- Scoring core: `src/scoring/{__init__,exact_match,partial_credit,result}.py`
  — commit `ef315f5`. 100% covered.
- Schema/migration: `src/models/answer.py`, `src/models/idempotency_key.py`,
  `sessions.submitted_at`, Alembic `0005_add_answers_idempotency_locking.py`
  — commit `6743b35`. Validated upgrade→downgrade→upgrade against Postgres.
- Single-question fetch: `src/utils/question_client.py::get_question` — commit
  `640609d`.
- Repos/schemas: `answer_repository.py`, `idempotency_repository.py`,
  `session_repository.get_for_update`/`flush`, `AnswerSubmit`/`AnswerResult`
  (score-free) — commit `a1c11fa`.
- Endpoint + service: `session_service.submit_answer`, `session_route` — commit
  `eb80e4e`. Gateway already routes `/sessions/*` (`api-gateway-service/main.py:55`).
- Tests: `tests/test_scoring.py`, `tests/test_answer_endpoint.py` — commit
  `af90a1f`. `pytest --cov` green (89 passed, 78.35% ≥ 75% gate); `ruff check .`
  clean.

## Notes

- Pure scoring functions are deliberately DB-free so the bulk of test coverage
  needs no fixtures — the endpoint tests (lock/idempotency) carry the
  integration weight, deepened against real Postgres in W3-F5.
- The scoring algorithm decision (exact vs. partial-credit / Jaccard) is a
  required ADR for W4-F5 — capture the rationale when implementing step 1.

## Remaining

None — all steps complete. Follow-ups owned by later features (not this one):
the real-Postgres `SELECT FOR UPDATE` concurrency race is exercised in W3-F5;
`PATCH /sessions/{id}/draft` (autosave) builds on this state machine in W3-F4;
free-text (`text`) questions are recorded with score `0.0` awaiting manual
grading (W4). Post-merge review hardening notes (2026-06-10) live in
[W3-F7 item 9](w3-f7-review-remediation.md): idempotency replay doesn't
fingerprint the request body, and the QMS question fetch runs while holding
the `SELECT FOR UPDATE` row lock — document or tighten both.
