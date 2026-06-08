# W3-F5 — Integration Tests Against Real Postgres & Mongo Containers

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §5 (Day 15)
**Depends on:** [W2-F2](w2-f2-unit-test-scaffolding.md) (Alembic fixture pattern + pytest-asyncio setup must be in place), [W2-F4](w2-f4-ci-quality-gates.md) (CI service-container pattern builds on the existing matrix job structure), W3-F1 + W3-F2 (the session-creation and answer-submission endpoints under test must be implemented)
**Unblocks:** W3-F6 (Playwright E2E — the smoke-script pattern established here is reused as the pre-flight health check before the browser run)
**Last updated:** 2026-06-08

Write pytest integration tests that exercise session creation, pessimistic
locking, and scoring against **real** database containers (not mocks), and wire
them into CI.

## Steps

- [ ] **1. Real-DB fixture** — pytest fixture that provisions a dedicated test
      Postgres database and runs `alembic upgrade head` before the test session.
      pytest-asyncio + SQLAlchemy async engine for test sessions.
- [ ] **2. Session-creation happy path** — seed a test + questions, `POST
      /sessions`, assert the returned `session_id` is a valid UUID and the
      `sessions` row has `expires_at == now + test.duration_seconds` (±1s).
- [ ] **3. Pessimistic-lock concurrency** — two concurrent asyncio tasks post
      the same answer to the same session; assert exactly one `200` and one
      `409`, with `current_index` advanced **exactly once**.
- [ ] **4. Idempotency** — post the same answer twice with the same
      `Idempotency-Key`; assert the session row is mutated exactly once.
- [ ] **5. CI integration step** — GitHub Actions matrix step that starts
      Postgres + Mongo service containers and runs `pytest --integration`
      before the Docker build, failing the pipeline on regression. Evidence:
      `.github/workflows/ci-pipeline.yml`.

## Notes

- These tests are the proving ground for the W3-F2 lock/idempotency claims —
  the unit tests cover pure scoring; only real Postgres exercises `SELECT FOR
  UPDATE` race behavior.
- Mongo container needed for the W3-F1 `$sample` cross-service call inside the
  session-creation test.

## Remaining

All steps.
