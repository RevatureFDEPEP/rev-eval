# Expected Milestones & Core Functionalities (Up to Day 15)

By Day 15, trainees are expected to have completed the full quiz-taking slice end to end. This means a candidate can log in, start a session, answer questions under a live countdown timer, submit their attempt, and see a locked result — all running against the real local Compose stack from Day 10.

1. Session Creation Backend (Day 11):
   * A POST /sessions endpoint in test-management-service that accepts a quiz ID, mints an opaque UUID session identifier, records server_now and expires_at in Postgres (not the client), and calls across to question-management-service via httpx to pull the first question.
   * Cross-service HTTP integration is established as a pattern, with explicit timeouts, bounded retries, and correlation-id header propagation.

2. Scoring Engine and Attempt Locking (Day 12):
   * Pure scoring functions for exact-match (single-select) and partial-credit (multi-select) questions, written without side effects or database access so they are trivially unit-testable.
   * Pessimistic locking (SELECT FOR UPDATE) on the session row during answer submission, preventing concurrent-tab and retry races from double-scoring a question.
   * Idempotency-key handling on POST /sessions/{id}/answer so that network retries do not duplicate scored answers.
   * State-machine enforcement: once a session reaches submitted or expired, all further answer mutations are rejected.

3. Test-Taking Frontend Skeleton (Day 13):
   * A dynamic Next.js route at /take/[testId] that mints the session server-side on first load and passes the resulting session state to a client TestRunner component as a prop, eliminating the loading flicker of a client-side fetch.
   * Polymorphic question rendering: a single dispatch site switches on question_type and renders either a radio-group (single-select) or a checkbox-group (multi-select) leaf component.
   * Multi-step navigation that keeps the candidate's answer selections in a client-side Map, allowing forward/back movement without re-fetching from the server and without losing prior selections.
   * Auth-context propagation so the session cookie reaches both the server-side mint call and every subsequent client-side answer submission without being exposed in JavaScript bundles.

4. Interactive Test-Taking with Timer and Autosave (Day 14):
   * A visible countdown timer derived from the server's expires_at and server_now values, not the client clock, recalculated on mount to absorb any clock skew.
   * Periodic autosave of in-progress answers to a PATCH /sessions/{id}/draft endpoint, executed on a debounced interval so that a browser crash or accidental close does not lose all work.
   * Submit-and-lock UX: on submission, all interactive form elements disable immediately, the timer stops, and a confirmation state is rendered before the server response returns.
   * Graceful network failure handling that classifies errors as transient (auto-retry with exponential backoff) versus semantic (surface to the user and halt) without flooding the server with retries on a 422.

5. Slice Integration and End-to-End Verification (Day 15):
   * A passing Playwright happy-path test that drives a real browser through login, session creation, answering all questions, and submission, validating the full vertical slice against a live Compose stack.
   * Integration tests in pytest that exercise the session-creation transaction and the pessimistic-lock race against real Postgres and Mongo containers, not mocks.
   * End-to-end smoke tests confirming all six containers (user-service, test-management-service, question-management-service, api-gateway, mongo, postgres) respond correctly in dependency order.

---

## Prioritized Feature Implementations for Days 11-15

The following 6 features are built exclusively using concepts taught in Days 1-15. They are listed in order of priority, starting with tasks that can be completed using topics available on Day 11, and ending with features that require Day 15 competencies.

### 1. Quiz Session Creation Backend
*Implement the POST /sessions endpoint that mints an opaque session token, records server-authoritative timing, and fetches the first question from question-management-service.*
* **Curriculum Fit**: Day 11 (Cross-service HTTP integration via httpx, opaque token generation, server-authoritative state, random sampling from MongoDB, FastAPI routing and dependency injection).
* **Prerequisites**: Day 11 topics.
* **Cross-Week Dependencies**: Requires W2-F7 (Alembic migrations & scaffolded domain) — the sessions table is a new migration on top of the existing test-management-service schema. Requires the Docker Compose topology from W2 (question-management-service and its MongoDB must be healthy for the cross-service httpx call to succeed). Requires W2-F5 (MinIO & question bank) — question-management-service must have seeded question documents for $sample to return results.
* **Required for**: W3-F2 (Scoring Engine — the sessions table and session_id must exist before the answer endpoint can lock and advance them), W3-F3 (Test-Taking Frontend Skeleton — the page calls POST /sessions server-side on load; the endpoint must return the correct contract shape)
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours
* **Implementation Details**:
  1. Add a sessions table to test-management-service (session_id UUID, test_id, user_id, session_token, server_now, expires_at, status, current_index) and generate a migration with Alembic.
  2. Implement POST /sessions in test-management-service. Generate the session_id with secrets.token_hex or uuid4, compute expires_at on the server from test.duration_seconds, and persist both before responding.
  3. In the same handler, call question-management-service via an httpx.AsyncClient singleton with an explicit timeout to retrieve question IDs using MongoDB's $sample aggregation and to fetch the first question body.
  4. Propagate the X-Correlation-Id header from the incoming request to all outbound httpx calls so distributed logs can be traced across services.
  5. Return the session_id, session_token, server_now, expires_at, and the first question in the response body. The client never computes or stores timing state directly.

### 2. Scoring Engine with Exact-Match and Partial-Credit Algorithms
*Build pure, deterministic scoring functions for single-select and multi-select questions, then wire them into the answer submission endpoint with pessimistic locking.*
* **Curriculum Fit**: Day 12 (Deterministic scoring, partial-credit algorithms, database transactions, pessimistic locking, idempotency for retried mutations, state finalization and immutability).
* **Prerequisites**: Day 12 topics.
* **Cross-Week Dependencies**: Requires W3-F1 (Quiz Session Creation Backend) — the sessions table, session_id, and current_index column must exist before the answer endpoint can lock and advance them. Requires W2-F2 (Unit Test Scaffolding) — pytest must already be configured in test-management-service for the parameterized scoring tests to run in CI.
* **Required for**: W3-F4 (Auto-Saving Exam Client — the PATCH /sessions/{id}/draft endpoint and session state machine established here are the base layer), W4-F1 (Candidate Results Reporting Endpoints — sessions and answers tables must be populated with scored data for aggregation queries), W4-F3 (Role-Based Authorization and Aggregate Queries — answers table data required for GROUP BY and window-function queries), W4-F5 (Technical Debt Audit — the scoring algorithm choice is one of the two required ADRs)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours
* **Implementation Details**:
  1. Create a scoring module in test-management-service (e.g., src/scoring/exact_match.py and src/scoring/partial_credit.py). Each file exposes a single pure function score_question(question_type, correct_answers, submitted_answers) -> ScoreResult with no database access or side effects.
  2. Implement the POST /sessions/{id}/answer endpoint. Wrap the read-modify-write in an explicit transaction and acquire a SELECT FOR UPDATE lock on the session row before reading current_index, so concurrent retries queue rather than race.
  3. Accept an Idempotency-Key header and store seen keys in a dedup table. On a duplicate key, return the prior response without re-scoring.
  4. After scoring, advance current_index. If it reaches the final question, transition session status to submitted, record submitted_at, and reject all further answer mutations with a 409.
  5. Write parameterized pytest cases covering exact-match, full-match, Jaccard, and partial-credit scenarios with a matrix of correct and incorrect answer combinations, using AI-assisted test authoring where appropriate.

### 3. Test-Taking Frontend Skeleton with Dynamic Routing and Auth Context
*Build the /take/[testId] Next.js page that mints a session server-side, renders questions polymorphically by type, and preserves answer state across forward and backward navigation.*
* **Curriculum Fit**: Day 13 (Dynamic routing with App Router parameters, server components for initial data fetching, polymorphic component rendering, multi-step navigation without state loss, authentication context propagation).
* **Prerequisites**: Day 13 topics.
* **Cross-Week Dependencies**: Requires W3-F1 (Quiz Session Creation Backend) — the page calls POST /sessions server-side on load; the endpoint must exist and return the correct contract shape. Requires W2-F1 (Nginx Routing) — the frontend must reach the API gateway through a single routed entry point rather than cross-origin direct port calls. Requires W2-F6 (Question Authoring Interface) — question documents must exist in MongoDB for a session to sample and render.
* **Required for**: W3-F4 (Auto-Saving Exam Client — the TestRunner component and answer Map state must exist as the base layer), W4-F2 (Candidate Results Page — the AuthContext provider and pep_session cookie forwarding pattern established here are reused), W4-F4 (Trainer Dashboard — the AuthContext provider supplies the role claim that drives client-side route guard rendering)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours
* **Implementation Details**:
  1. Create frontend/app/take/[testId]/page.tsx as an async server component. On render, read the pep_session cookie from next/headers and POST /sessions to test-management-service server-side, so the first question is in the initial HTML with no client spinner.
  2. Pass the resulting session object as a prop to a <TestRunner> client component that owns all interactive state: currentIndex (number) and answers (Map<string, number[]>).
  3. Inside TestRunner, implement a single dispatch function renderQuestion(question) that switches on question.type and renders either a <SingleSelectQuestion> (radio group) or <MultiSelectQuestion> (checkbox group) leaf component.
  4. Implement Previous / Next navigation by incrementing or decrementing currentIndex in React state only, with no App Router navigation calls, so selections in the answers Map are preserved across question switches.
  5. Create an AuthContext provider that reads display identity (user_id, email, role) from a server-fetched token validation call and exposes it to the client tree without ever placing the raw session cookie into window or JavaScript bundles.

### 4. Auto-Saving Exam Client with Server-Anchored Timer and Submit-Lock UX
*Layer a live countdown timer derived from server timing, periodic autosave, graceful network failure handling, and an immediate submit-and-lock interaction on top of the Day 13 skeleton.*
* **Curriculum Fit**: Day 14 (Client-side temporal state and timers, submit-and-lock UX patterns, graceful network failure handling, optimistic updates vs. server confirmation, React state management with useReducer, component unit testing with Vitest).
* **Prerequisites**: Day 14 topics.
* **Cross-Week Dependencies**: Requires W3-F3 (Test-Taking Frontend Skeleton) — the TestRunner component and answer Map state must exist as the base layer this feature extends. Requires W3-F2 (Scoring Engine) — the PATCH /sessions/{id}/draft endpoint relies on the session state machine and status fields introduced in W3-F2; the submit-lock UX is only meaningful once the server-side submitted state is enforced.
* **Required for**: W3-F6 (Playwright E2E and Smoke Script — the full quiz-taking UI including timer and submit-lock must be in place for the happy-path flow to complete)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours
* **Implementation Details**:
  1. On TestRunner mount, compute the remaining seconds as (expires_at - server_now) - (Date.now() / 1000 - mount_time) to absorb client clock skew. Run a setInterval decrement and render the remaining time. When the counter reaches zero, call the submit handler automatically.
  2. Add a PATCH /sessions/{id}/draft endpoint to test-management-service that accepts a partial answers payload and persists it without advancing current_index or changing session status. Wire a debounced autosave call from TestRunner on a 30-second interval.
  3. Classify fetch errors into transient (network timeouts, 502/503/504 — retry with exponential backoff) and semantic (409 Conflict, 410 Gone, 422 Validation — surface immediately and halt) so retries are only issued where they can succeed.
  4. On submit, immediately set a isLocked: true flag in component state (using useReducer for the full session state machine) before the server responds, disabling all inputs and the timer. Autosave is a confirmed update (wait for server ack before clearing draft); submission is also confirmed (do not unlock until the server confirms, to avoid prematurely showing a result that was rejected).
  5. Write Vitest component unit tests for the timer decrement logic, the autosave debounce trigger, and the locked state rendering, asserting DOM attributes (disabled, aria-disabled) on interactive elements when isLocked is true.

### 5. Integration Tests Against Real Postgres and Mongo Containers
*Write pytest integration tests that exercise session creation, pessimistic locking, and scoring against real database containers rather than mocks, and wire them into CI.*
* **Curriculum Fit**: Day 15 (Integration testing against local data stores, vertical-slice integration in Compose, effective code review practice).
* **Prerequisites**: Day 15 topics.
* **Cross-Week Dependencies**: Requires W2-F2 (Unit Test Scaffolding) — Alembic fixture pattern and pytest-asyncio setup must already be in place in test-management-service. Requires W2-F4 (Ruff/ESLint/Trivy CI) — the CI service-container pattern for Postgres and Mongo in GitHub Actions builds on the existing matrix job structure. Requires W3-F1 and W3-F2 — the session creation and answer submission endpoints being tested must be fully implemented.
* **Required for**: W3-F6 (Playwright E2E and Smoke Script — the smoke script pattern established here is reused as the pre-flight health check before Playwright runs)
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours
* **Implementation Details**:
  1. Add a pytest fixture that provisions a dedicated test Postgres database and runs Alembic upgrade head before each test session. Use pytest-asyncio and SQLAlchemy's async engine for test sessions.
  2. Write an integration test for the session creation happy path: seed a test and questions, POST /sessions, assert the returned session_id is a valid UUID, and assert the sessions row in Postgres has expires_at set to now + test.duration_seconds within one second.
  3. Write a concurrency integration test for the pessimistic lock: launch two concurrent asyncio tasks both posting the same answer to the same session and assert that exactly one succeeds with 200 and the other receives a 409, with current_index advanced exactly once.
  4. Write an integration test for idempotency: post the same answer twice with the same Idempotency-Key header and assert the session row is mutated exactly once.
  5. Add a CI step to the GitHub Actions matrix that starts Postgres and Mongo service containers and runs pytest --integration before the Docker build step, failing the pipeline on any regression.

### 6. Playwright End-to-End Happy-Path Test and Smoke Script
*Write a Playwright test that drives a real browser through the full quiz-taking vertical slice against the live Compose stack, and wire it into CI alongside a service smoke test.*
* **Curriculum Fit**: Day 15 (End-to-end UI testing with Playwright happy-path, end-to-end smoke testing patterns, distributed log analysis across services, vertical-slice integration).
* **Prerequisites**: Day 15 topics.
* **Cross-Week Dependencies**: Requires W2-F1 (Nginx Routing) — Playwright navigates through port 80/443 as a browser would; the single entry point must be wired or the test must target port 3000 directly with CORS issues bypassed. Requires W3-F3 and W3-F4 (Frontend Skeleton + Timer/Autosave) — the full quiz-taking UI must be in place for the happy-path flow to complete. Requires W3-F5 (Integration Tests) — the smoke script pattern established there is reused as the pre-flight health check before Playwright runs.
* **Time Estimate**: Without AI tools: 5–8 hours | With AI tools (Gemini/Claude Code): 2–4 hours
* **Implementation Details**:
  1. Install Playwright in the frontend package (npx playwright install --with-deps) and create playwright.config.ts pointing at http://localhost:3000 with the Chromium project as the default.
  2. Write one Playwright test in tests/e2e/quiz-taking.spec.ts covering the happy path: navigate to /login, fill credentials for a seeded candidate user, assert redirect to dashboard, click Start on an assigned test, answer all questions using page.locator and page.click, click Submit, and assert the result page shows a score summary with all inputs disabled.
  3. Write a shell-script smoke test (test-services.sh extension or a separate script) that curls the /health endpoint of every service in dependency order and exits non-zero if any service returns a non-200 status, so the Playwright test only runs against a confirmed-healthy stack.
  4. Wire the smoke test and Playwright test as a sequential CI job that depends on the build matrix completing successfully and uses docker compose up -d --wait to ensure the full stack is healthy before the browser tests execute.
  5. After each Playwright test run, capture distributed logs from all containers using docker compose logs --no-color > e2e-run.log and upload the log file as a CI artifact so failures can be traced across service boundaries without re-running locally.
