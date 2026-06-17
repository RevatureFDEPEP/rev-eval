# W3-F5 — Integration Tests Against Real Postgres and Mongo Containers

*Write pytest integration tests that exercise session creation, pessimistic locking, and scoring against real database containers rather than mocks, and wire them into CI.*

* **Curriculum Fit**: Day 15 (Integration testing against local data stores, vertical-slice integration in Compose, effective code review practice).
* **Prerequisites**: Day 15 topics.
* **Cross-Week Dependencies**: Requires W2-F2 (Unit Test Scaffolding) — Alembic fixture pattern and pytest-asyncio setup must already be in place in test-management-service. Requires W2-F4 (Ruff/ESLint/Trivy CI) — the CI service-container pattern for Postgres and Mongo in GitHub Actions builds on the existing matrix job structure. Requires W3-F1 and W3-F2 — the session creation and answer submission endpoints being tested must be fully implemented.
* **Required for**: W3-F6 (Playwright E2E and Smoke Script — the smoke script pattern established here is reused as the pre-flight health check before Playwright runs)
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours

## Implementation Details

1. Add a pytest fixture that provisions a dedicated test Postgres database and runs `alembic upgrade head` before each test session. Use pytest-asyncio and SQLAlchemy's async engine for test sessions.
2. Write an integration test for the session creation happy path: seed a test and questions, `POST /sessions`, assert the returned `session_id` is a valid UUID, and assert the sessions row in Postgres has `expires_at` set to `now + test.duration_seconds` within one second.
3. Write a concurrency integration test for the pessimistic lock: launch two concurrent asyncio tasks both posting the same answer to the same session and assert that exactly one succeeds with 200 and the other receives a 409, with `current_index` advanced exactly once.
4. Write an integration test for idempotency: post the same answer twice with the same `Idempotency-Key` header and assert the session row is mutated exactly once.
5. Add a CI step to the GitHub Actions matrix that starts Postgres and Mongo service containers and runs `pytest --integration` before the Docker build step, failing the pipeline on any regression.
