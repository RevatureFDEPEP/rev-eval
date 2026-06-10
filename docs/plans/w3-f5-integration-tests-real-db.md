# W3-F5 — Integration Tests Against Real Postgres & Mongo Containers

**Feature:** [docs/features/w3-f5-integration-tests-real-db.md](../features/w3-f5-integration-tests-real-db.md)
— spec `days_11_15_features.md` §5 (Day 15).
**Depends on:** W2-F2 (pytest-asyncio scaffolding) ✅, W2-F4 (CI matrix) ✅,
W3-F1 + W3-F2 (sessions + scoring/locking endpoints) ✅ — all complete.
**Unblocks:** W3-F6 (Playwright E2E — reuses the healthy-stack pre-flight pattern).

Write pytest integration tests that exercise session creation, pessimistic
locking, and idempotency against **real** Postgres and Mongo (via the real
question-management-service), and wire them into CI — failing the pipeline
before the Docker build on any regression.

## Context

What exists now:

- **Unit tests are hermetic**: `services/test-management-service/conftest.py:26`
  builds an in-memory SQLite engine (`StaticPool`); the question-service httpx
  client is mocked. 94 tests pass. No `integration` marker, no `--integration`
  flag, nothing touches a real DB.
- **Endpoints under test are done**: `POST /sessions`
  (`src/v1/routes/session_route.py:29`), `POST /sessions/{id}/answer`
  (`session_route.py` answer handler), pessimistic lock via
  `SessionRepository.get_for_update` (`src/repositories/session_repository.py:44`,
  `.with_for_update()`), idempotency dedup table
  (`src/models/idempotency_key.py`, checked inside the lock at
  `src/services/session_service.py:150`).
- **Alembic chain** `0001`–`0006` owns the schema; `alembic/env.py:35` resolves
  the URL from the `DATABASE_URL` env var (forces asyncpg).
- **CI** (`.github/workflows/ci-pipeline.yml`): per-service matrix job runs
  Ruff → `pytest --cov` (hermetic) → `docker build --target test` → prod build
  → Trivy. No databases in CI today.
- **Compose** (source of truth): `postgres:15-alpine` (root/root,
  `eval_ai_dev`, port 5432, `pg_isready` healthcheck), `mongo:7` (port 27017,
  `mongosh ping` healthcheck), `question-management-service` on 8003
  (healthcheck `/health`; MinIO bucket init is non-fatal `try/except`).

Key constraints discovered during analysis (these shape the design):

1. **Alembic `0003` (seed) queries the `users` table**, which is owned by
   user-service and absent from this service's metadata. On a fresh, empty test
   database `alembic upgrade head` **fails** at `_trainer_id()`
   (`alembic/versions/0003_seed_demo_data.py:297` — raises when no TRAINER
   exists). The fixture must create a stub `users` table with one TRAINER and
   two PARTICIPANT rows *before* running migrations — mirroring the
   user-service-first startup ordering that compose guarantees in production.
2. **409 semantics**: the answer endpoint returns 409 only from the
   terminal/expired state gate (`SessionTerminalError`/`SessionExpiredError` →
   `session_route.py:117`). There is no per-request `question_index` check —
   on a multi-question session, a second concurrent submission would simply
   score the *next* question and also get 200. Therefore the concurrency test
   must use a **single-question session**: request A scores question 0,
   finalizes the session to `SUBMITTED`; request B (queued on `FOR UPDATE`)
   then hits the terminal gate → 409, with `current_index` advanced exactly
   once. This is the spec's "exactly one 200 and one 409" expressed through
   the real state machine.
3. **Scoring reads `correct_answers` from the real question-service**
   (`session_service.py` step 4 → `question_client.get_question(qid)`). Unit
   tests mock this client, so the *real* cross-service contract (including
   Mongo `$sample` for session creation) has never been exercised — exactly
   what this feature is for. The question-service `QuestionRead` schema does
   include `correct_answers`, so the contract should hold; the integration
   test is the proof.
4. **Settings/client are import-time singletons**: `question_client.get_client()`
   caches an `httpx.AsyncClient` with `base_url=settings.QUESTION_SERVICE_URL`,
   and `src/config/settings.py` reads env at import. The integration conftest
   must set `DATABASE_URL` / `QUESTION_SERVICE_URL` env vars **before** the app
   modules are imported (and/or reset the client singleton per session).
5. **The Dockerfile test stage runs plain `pytest -q`** with no databases —
   integration tests must auto-skip unless explicitly enabled, or every
   container build breaks.

## Design decisions

- **Gating:** a custom `--integration` pytest CLI flag (registered in the root
  `conftest.py` via `pytest_addoption`) plus an `integration` marker registered
  in `pytest.ini`. A `pytest_collection_modifyitems` hook skips
  `@pytest.mark.integration` tests when the flag is absent. Plain `pytest`
  (unit CI step, Docker test stage) is unchanged; `pytest --integration -m
  integration` runs only the integration suite — matching the spec's
  `pytest --integration` wording.
- **Real services come from Docker Compose**, not hand-rolled GHA `services:`
  blocks: a CI step runs `docker compose up -d --wait postgres mongo
  question-management-service` (compose pulls in Mongo/MinIO deps and reuses
  the existing healthchecks). This starts the Postgres and Mongo containers the
  spec asks for *and* the real question-service needed for the `$sample`
  cross-service call, with one command that works identically on a dev machine.
- **Dedicated test database** `eval_ai_itest`: a session-scoped fixture
  connects to the admin `postgres` database (asyncpg, autocommit), `DROP
  DATABASE IF EXISTS` + `CREATE DATABASE`, creates the stub `users` table +
  demo TRAINER/PARTICIPANT rows, then runs `alembic upgrade head` as a
  **subprocess** with `DATABASE_URL` pointed at the test DB (subprocess avoids
  nesting Alembic's `asyncio.run` inside the pytest-asyncio loop). The dev
  `eval_ai_dev` volume is never touched.
- **App exercised in-process** via `httpx.AsyncClient(transport=ASGITransport(app))`
  with the `get_db` dependency overridden to a sessionmaker bound to the test
  engine — each request gets its own session/connection, so `SELECT FOR
  UPDATE` contention between two concurrent ASGI requests is real Postgres
  row-lock behavior. Auth via `X-User-Id`/`X-User-Email`/`X-User-Role` headers
  (the gateway-trust model; no JWT needed below the gateway).
- **Mongo seeding** directly via `pymongo` (added to `requirements-dev.txt`):
  insert MCQ/MULTI question documents shaped like the Beanie `Question`
  document (mirror `seed_rag_context_questions.py`), tagged with a unique
  test-run marker field for teardown. `$sample` may also return pre-existing
  dev documents — tests assert on *session* invariants (UUID, expiry, counts),
  never on which questions were sampled.

## Implementation steps

### 0. Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create feature branch **`richardh-feat-W3F5`** off `richardh` before any code
  change; confirm with `git branch --show-current`.
- **First commit on the branch = this plan file** (`docs/plans/w3-f5-integration-tests-real-db.md`).
- One commit per milestone below, Conventional Commits style.

### M1 — Integration harness (gating + fixtures)

Files: `services/test-management-service/conftest.py` (add option/hook only —
unit fixtures untouched), `pytest.ini` (register `integration` marker),
`requirements-dev.txt` (+`pymongo`), new
`services/test-management-service/tests/integration/__init__.py` + `conftest.py`.

1. `--integration` flag + marker + auto-skip hook (root `conftest.py`,
   `pytest.ini`).
2. `tests/integration/conftest.py` (all fixtures session-scoped unless noted):
   - env knobs with compose-default fallbacks:
     `IT_POSTGRES_ADMIN_URL` (default `postgresql://root:root@localhost:5432/postgres`),
     `IT_DATABASE_URL` (default `postgresql+asyncpg://root:root@localhost:5432/eval_ai_itest`),
     `IT_MONGO_URI` (default `mongodb://localhost:27017`),
     `IT_QUESTION_SERVICE_URL` (default `http://localhost:8003`).
   - `pg_database`: admin connect → drop/create `eval_ai_itest` → stub `users`
     table (+1 TRAINER, 2 PARTICIPANTs) → `alembic upgrade head` subprocess with
     `DATABASE_URL` set. Fails fast with a clear message if Postgres is
     unreachable ("run `docker compose up -d --wait postgres mongo
     question-management-service`").
   - `engine` / `db_sessionmaker`: async engine on `IT_DATABASE_URL`.
   - `app_client`: set `QUESTION_SERVICE_URL` env + reset the
     `question_client` singleton, import the app, override `get_db` to mint a
     fresh `AsyncSession` per request, yield
     `httpx.AsyncClient(transport=ASGITransport(app), base_url="http://test")`.
   - `mongo_questions` (function-scoped): pymongo insert N tagged question
     docs into the question-service DB/collection; health-check
     `GET {IT_QUESTION_SERVICE_URL}/health` first; delete tagged docs on
     teardown.
   - `seeded_test` (function-scoped): insert a `Test` row (known `duration`,
     parametrizable `number_of_questions`) via the test engine; delete on
     teardown.

Commit: `test(w3-f5): integration harness — --integration gate, real-Postgres
Alembic fixture, Mongo seeding`

### M2 — Session-creation happy path (spec step 2)

File: `tests/integration/test_session_creation_it.py`.

- Seed test (e.g. `duration=30min`, `number_of_questions=3`) + ≥3 Mongo
  questions → `POST /v1/api/sessions/` → assert 201, `session_id` parses as
  `uuid.UUID`, response carries first question with no `correct_answers` leak.
- Read the `sessions` row back via the test engine: assert
  `expires_at == server_now + duration` exactly (server-computed) and
  `expires_at ≈ utcnow() + duration` within **±1s** (spec tolerance);
  `status == ACTIVE`, `current_index == 0`, `len(question_ids) == 3`.

Commit: `test(w3-f5): session-creation happy path against real Postgres+Mongo`

### M3 — Pessimistic-lock concurrency + idempotency (spec steps 3–4)

File: `tests/integration/test_answer_concurrency_it.py`.

- **Concurrency:** single-question session (`number_of_questions=1`). Create
  session, then `asyncio.gather` two `POST /answer` for the same payload with
  **different** `Idempotency-Key`s. Assert `sorted(status_codes) == [200, 409]`;
  re-read row: `current_index == 1`, `status == SUBMITTED`, exactly **one**
  `answers` row for the session.
- **Idempotency:** multi-question session. Two sequential `POST /answer` with
  the **same** `Idempotency-Key`. Assert both 200 with byte-identical bodies
  (stored-response replay), `current_index == 1` (mutated once), one `answers`
  row, one `idempotency_keys` row.

Commit: `test(w3-f5): FOR-UPDATE concurrency (one 200/one 409) + idempotent
replay against real Postgres`

### M4 — CI integration step (spec step 5)

File: `.github/workflows/ci-pipeline.yml` (backend matrix job).

- New steps **after** unit `pytest --cov`, **before** `docker build`, gated
  `if: matrix.service == 'test-management-service'`:
  1. `cp .env.example .env && docker compose up -d --wait postgres mongo
     question-management-service` (waits on existing healthchecks).
  2. `pytest --integration -m integration -v` from the service dir (env:
     the `IT_*` localhost defaults already match the published compose ports).
  3. `docker compose down -v` (always(), teardown) + dump
     `docker compose logs` on failure for diagnosis.
- Any integration failure fails the job before the Docker build/Trivy steps —
  the spec's regression gate.

Commit: `ci(w3-f5): run integration suite vs compose Postgres+Mongo before
Docker build`

### M5 — Requirements review + docs

- Re-read `docs/features/w3-f5-integration-tests-real-db.md` Steps 1–5 + spec
  §5 implementation details; verify each against the diff with file:line +
  commit evidence.
- Update the feature detail doc (check off steps, add evidence, update
  Remaining) and the `FEATURE_STATUS.md` W3-F5 row + "Last assessed" note.

Commit: `docs(w3-f5): mark feature complete + requirements review evidence`

## Testing & validation

| Check | Command (from `services/test-management-service/`) | Pass bar |
|---|---|---|
| Integration suite | `docker compose up -d --wait postgres mongo question-management-service` (repo root), then `pytest --integration -m integration -v` | all integration tests pass against real containers |
| Unit suite unaffected | `pytest --cov` (no flag) | all 94 existing tests still pass; integration tests reported as skipped |
| Hermetic container build | `docker build --target test .` | image test stage green with no DB available (proves the gate) |
| Lint | `ruff check .` | clean |
| CI dry-run reasoning | re-read workflow diff | integration step ordered before Docker build, scoped to test-management-service |

Flakiness guard: the concurrency test runs the race once but asserts a
deterministic outcome (lock serializes; single-question session forces the
loser into the terminal gate) — no sleeps, no timing assertions beyond the
spec's ±1s expiry tolerance.

## Push gate

Push `richardh-feat-W3F5` to origin **only if** every row in the table above
passes **and** the M5 requirements review confirms all five feature-doc steps
with evidence. Otherwise stop, leave the branch local, and report exactly
what's outstanding.
