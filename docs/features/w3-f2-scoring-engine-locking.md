# W3-F2 — Scoring Engine with Exact-Match & Partial-Credit + Attempt Locking

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §2 (Day 12)
**Depends on:** W3-F1 (sessions table, `session_id`, `current_index` must exist before the answer endpoint can lock and advance them), [W2-F2](w2-f2-unit-test-scaffolding.md) (pytest must be configured in test-management-service for the parameterized scoring tests to run in CI)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `PATCH /sessions/{id}/draft` + the session state machine established here are the base layer), W4-F1 (Results Reporting — sessions/answers must hold scored data), W4-F3 (Role-Based Aggregate Queries — answers data for `GROUP BY`/window functions), W4-F5 (Tech Debt Audit — scoring algorithm choice is one required ADR)
**Last updated:** 2026-06-08

Build pure, deterministic scoring functions for single-select (exact-match) and
multi-select (partial-credit) questions, then wire them into the answer
submission endpoint with pessimistic locking, idempotency, and state
finalization.

## Steps

- [ ] **1. Pure scoring module** — `src/scoring/exact_match.py` and
      `src/scoring/partial_credit.py`, each exposing a single pure
      `score_question(question_type, correct_answers, submitted_answers) ->
      ScoreResult` with **no DB access or side effects** (trivially
      unit-testable).
- [ ] **2. POST /sessions/{id}/answer + pessimistic lock** — wrap
      read-modify-write in an explicit transaction; acquire `SELECT FOR UPDATE`
      on the session row **before** reading `current_index` so concurrent
      retries queue rather than race (prevents double-scoring from
      concurrent-tab / retry).
- [ ] **3. Idempotency** — accept an `Idempotency-Key` header; store seen keys
      in a dedup table. On duplicate key, return the prior response without
      re-scoring.
- [ ] **4. State machine + finalization** — after scoring, advance
      `current_index`. On the final question, transition `status` →
      `submitted`, record `submitted_at`, and reject all further answer
      mutations with `409`. `submitted`/`expired` are terminal.
- [ ] **5. Parameterized pytest** — matrix over exact-match, full-match,
      Jaccard, and partial-credit scenarios with correct/incorrect answer
      combinations. Evidence: `tests/test_scoring.py` (pure-function level),
      `tests/test_answer_endpoint.py` (lock/idempotency/state).

## Notes

- Pure scoring functions are deliberately DB-free so the bulk of test coverage
  needs no fixtures — the endpoint tests (lock/idempotency) carry the
  integration weight, deepened against real Postgres in W3-F5.
- The scoring algorithm decision (exact vs. partial-credit / Jaccard) is a
  required ADR for W4-F5 — capture the rationale when implementing step 1.

## Remaining

All steps.
