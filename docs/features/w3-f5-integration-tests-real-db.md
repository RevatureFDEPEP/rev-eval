# W3-F5 — Integration Tests Against Real Postgres & Mongo Containers

**Status:** ✅ Completed
**Spec:** `days_11_15_features.md` §5 (Day 15)
**Depends on:** [W2-F2](w2-f2-unit-test-scaffolding.md) (Alembic fixture pattern + pytest-asyncio setup must be in place), [W2-F4](w2-f4-ci-quality-gates.md) (CI service-container pattern builds on the existing matrix job structure), W3-F1 + W3-F2 (the session-creation and answer-submission endpoints under test must be implemented)
**Unblocks:** W3-F6 (Playwright E2E — the smoke-script pattern established here is reused as the pre-flight health check before the browser run)
**Plan:** [docs/plans/w3-f5-integration-tests-real-db.md](../plans/w3-f5-integration-tests-real-db.md)
**Last updated:** 2026-06-10

Write pytest integration tests that exercise session creation, pessimistic
locking, and scoring against **real** database containers (not mocks), and wire
them into CI.

## Steps

- [x] **1. Real-DB fixture** — pytest fixture that provisions a dedicated test
      Postgres database and runs `alembic upgrade head` before the test session.
      pytest-asyncio + SQLAlchemy async engine for test sessions.
      *Evidence:* `tests/integration/conftest.py` — session-scoped `pg_database`
      drops/recreates `eval_ai_itest` (asyncpg admin connection, `WITH (FORCE)`)
      and runs `alembic upgrade head` as a subprocess; `it_db` yields an async
      `NullPool` engine/sessionmaker. A stub `users` table (1 TRAINER, 2
      PARTICIPANTs) is created first because Alembic `0003`'s demo seed looks up
      user-service-owned rows. Gated by a `--integration` flag + `integration`
      marker (root `conftest.py`, `pytest.ini`) so plain `pytest` — the unit CI
      step and the Dockerfile `test` stage — auto-skips. Commit `b1abcb0`.
- [x] **2. Session-creation happy path** — seed a test + questions, `POST
      /sessions`, assert the returned `session_id` is a valid UUID and the
      `sessions` row has `expires_at == now + test.duration_seconds` (±1s).
      *Evidence:* `tests/integration/test_session_creation_it.py` — questions
      seeded directly in Mongo (pymongo, tagged + cleaned up), the POST runs the
      real httpx → question-management-service → `$sample` path; asserts
      `uuid.UUID(...)` parses, `expires_at == server_now + duration` exactly and
      within ±1s of wall clock, and the sanitized first question carries no
      `correct_answers`/`sample_answer`. Commit `76a3d9a`.
- [x] **3. Pessimistic-lock concurrency** — two concurrent asyncio tasks post
      the same answer to the same session; assert exactly one `200` and one
      `409`, with `current_index` advanced **exactly once**.
      *Evidence:* `tests/integration/test_answer_concurrency_it.py::
      test_concurrent_answers_serialize_one_200_one_409` — a single-question
      session makes the race observable through the state machine (the answer
      endpoint has no per-request index check, so on a longer session the lock
      loser would score the next question and also 200): the `FOR UPDATE`
      winner scores + finalizes (200), the loser queues on the row lock and
      hits the terminal gate (409); `current_index == 1`, one `answers` row.
      Commit `095f489`.
- [x] **4. Idempotency** — post the same answer twice with the same
      `Idempotency-Key`; assert the session row is mutated exactly once.
      *Evidence:* same file, `test_same_idempotency_key_mutates_session_exactly_once`
      — both responses 200 with identical bodies (stored-response replay), one
      `answers` row, one `idempotency_keys` row, `current_index == 1`.
      Commit `095f489`.
- [x] **5. CI integration step** — GitHub Actions matrix step that starts
      Postgres + Mongo service containers and runs `pytest --integration`
      before the Docker build, failing the pipeline on regression. Evidence:
      `.github/workflows/ci-pipeline.yml`.
      *Evidence:* steps gated to the `test-management-service` matrix entry:
      `docker compose up -d --wait postgres mongo question-management-service`
      (compose is the source of truth for images/env/healthchecks; the question
      service rides along for the real `$sample` cross-service call), then
      `pytest --integration -m integration -v`, with `docker compose logs`
      dumped on failure and `docker compose down -v` teardown — ordered before
      the `docker build` steps. Commit `5f1afe7`.

## Notes

- These tests are the proving ground for the W3-F2 lock/idempotency claims —
  the unit tests cover pure scoring; only real Postgres exercises `SELECT FOR
  UPDATE` race behavior.
- Mongo container needed for the W3-F1 `$sample` cross-service call inside the
  session-creation test.
- Connection knobs (`IT_DATABASE_URL`, `IT_MONGO_URI`, `IT_QUESTION_SERVICE_URL`,
  …) default to the published compose ports; see the
  `tests/integration/conftest.py` docstring. `Settings()` is instantiated while
  pytest loads `tests/conftest.py`, before any hook can export env — so the
  integration targets are rebound at fixture time (`settings.QUESTION_SERVICE_URL`
  + question-client singleton rebuild), not via `pytest_configure`.
- Two deliberate dependency overrides in `app_client`: `get_db` → per-request
  sessions on the integration engine (real row-lock contention), and
  `get_current_user_from_headers` → header-driven stub (the production
  dependency resolves users by calling user-service over HTTP; that hop is out
  of scope for this suite).

## Verification (2026-06-10)

- `pytest --integration -m integration -v` vs live compose containers: **4 passed**.
- `pytest --cov` (no flag): **94 passed, 4 skipped**, coverage 75.24% (≥75 gate).
- `docker build --target test .`: green — in-container `pytest -q` auto-skips
  the integration suite with no databases available.
- `ruff check .`: clean.

## Remaining

None.
