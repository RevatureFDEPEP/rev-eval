# Test Management Service

A FastAPI service on port **8001** and the core of the assessment workflow: tests, skills, assignments, timed test sessions, submissions, scoring and trainer review. Data is stored in PostgreSQL (SQLAlchemy, Alembic migrations).

## Responsibilities

| Area | Routes (under `/v1/api`) |
|------|--------------------------|
| Tests | `/tests` (create, list, update, delete, list by creator) |
| Skills | `/skills` |
| Assignment and review | `/submissions` (bulk assign, graded, evaluated, trainer review) |
| Timed sessions | `/test-sessions` (create, status, Part A and Part B questions, draft autosave, submit) |

`src/v1/routes/dashboard_route.py` is not mounted (its handlers are commented out), so `/dashboard/*` returns `404`.

## Who can call what

Every route needs the caller's own Bearer JWT, which this service verifies and resolves through user-service; `X-User-*` headers are not used for identity.

- **Trainers** create tests and manage (update, delete, assign, review, grade) the tests they created.
- **Participants** read only the tests assigned to them and their own submissions, and start, answer, autosave and submit only their own quiz sessions.
- The skill catalogue is readable by any signed-in user and changed only by trainers.

Rules live in `src/utils/authorization.py`; `tests/test_authorization.py` covers them, including that refused writes leave the database unchanged. Details: [SECURITY.md](../../docs/SECURITY.md).

## How scoring and submission behave

- **Scoring:** single-answer questions are exact match; multi-select questions earn partial credit using Jaccard similarity.
- **Idempotent submits:** a submit that carries an `Idempotency-Key` header is stored as a SHA-256 hash per part, and repeating the same key replays the original result instead of scoring again.
- **Locking:** the session row is read with `SELECT ... FOR UPDATE` when a submit finalizes it, so concurrent submits for one session cannot both score it.

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). `start.sh` waits for the database, creates the tables and runs `seed_db.py`, which loads synthetic demo users and sample tests for local development only.

```bash
cd services/test-management-service
pip install -r requirements.txt pytest pytest-cov aiosqlite
pytest        # includes scoring, session-lock and Postgres integration tests; fails below 80 % coverage
```

The Postgres tests use the `DB_*` environment variables, as CI does.
