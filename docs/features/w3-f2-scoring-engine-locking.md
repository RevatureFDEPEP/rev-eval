# W3-F2 — Scoring Engine with Exact-Match & Partial-Credit + Attempt Locking

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §2 (Day 12)
**Depends on:** W3-F1 (sessions table, `session_id`, `current_index` must exist before the answer endpoint can lock and advance them), [W2-F2](w2-f2-unit-test-scaffolding.md) (pytest must be configured in test-management-service for the parameterized scoring tests to run in CI)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `PATCH /sessions/{id}/draft` + the session state machine established here are the base layer), W4-F1 (Results Reporting — sessions/answers must hold scored data), W4-F3 (Role-Based Aggregate Queries — answers data for `GROUP BY`/window functions), W4-F5 (Tech Debt Audit — scoring algorithm choice is one required ADR)
**Last updated:** 2026-06-12

Scoring logic + attempt-locking for quiz sessions.

## Steps

- [ ] **1. Pure scoring module** — `score_answer(question, response)` supporting
      exact-match (MCQ/TRUE_FALSE) and partial-credit (MULTI).
- [ ] **2. POST /sessions/{id}/answer + pessimistic lock** — `SELECT FOR UPDATE`
      on the session row; validate `current_index`, apply score, advance index.
- [ ] **3. Idempotency** — re-submitting the same index returns the cached score
      without re-locking.
- [ ] **4. State machine + finalization** — session transitions
      `active → submitted` when all questions answered; `score_total` computed.
- [ ] **5. Parameterized pytest** — test every score branch (exact, partial, zero,
      boundary) using the in-memory DB fixture from [W2-F2](w2-f2-unit-test-scaffolding.md).

## Evidence

None on `tianyac` branch. Blocked on W3-F1 (no sessions table).

## Remaining

All steps.
