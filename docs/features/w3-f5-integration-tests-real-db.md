# W3-F5 — Integration Tests Against Real Postgres & Mongo Containers

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §5 (Day 15)
**Depends on:** [W2-F2](w2-f2-unit-test-scaffolding.md) (Alembic fixture pattern + pytest-asyncio setup must be in place), [W2-F4](w2-f4-ci-quality-gates.md) (CI service-container pattern builds on the existing matrix job structure), W3-F1 + W3-F2 (the session-creation and answer-submission endpoints under test must be implemented)
**Unblocks:** W3-F6 (Playwright E2E — the smoke-script pattern established here is reused as the pre-flight health check before the browser run)
**Last updated:** 2026-06-12

Extend the test suite to hit real Postgres and Mongo service containers in CI,
replacing the in-memory mocks from [W2-F2](w2-f2-unit-test-scaffolding.md) for
the session-creation and scoring endpoints.

## Steps

- [ ] **1. Real-DB fixture** — `conftest.py` `pytest-postgresql` + Alembic
      `upgrade head` fixture; `pytest-asyncio` motor client for Mongo.
- [ ] **2. Session-creation happy path** — `POST /sessions` with a real Postgres
      transaction and a real Mongo `$sample` call.
- [ ] **3. Pessimistic-lock concurrency** — two concurrent `POST /answer` calls
      for the same session; verify only one advances `current_index`.
- [ ] **4. Idempotency** — re-POST the same answer; verify score unchanged.
- [ ] **5. CI integration step** — add `services: postgres, mongo` to the
      test-management-service matrix job; run `pytest -m integration`.

## Evidence

None on `tianyac` branch. Blocked on W3-F1 + W3-F2 (no session backend).
Current backend tests use in-memory mocks ([W2-F2](w2-f2-unit-test-scaffolding.md)).

## Remaining

All steps.
