# Week 3 Prioritized Feature Plan (Days 11–15)

## Already Built — Do Not Touch

- **Day 11 BE**: Quiz session creation, opaque token, random question sampling from MongoDB, cross-service HTTP calls via `httpx`, server-authoritative state machine — all solid in `quiz_session_route.py` / `quiz_session_service.py`.
- **Day 12 BE**: Exact-match + partial-credit scoring, idempotency, `SELECT FOR UPDATE` locking, state finalization via `SessionStatus` enum — all in place in `quiz_answer_service.py` and `src/scoring/`.
- **Day 13 FE skeleton**: Quiz page exists at `frontend/src/app/(dashboard)/participant/tests/take/mcq/[testId]/page.tsx` with all components present (`Timer`, `QuestionCard`, `QuestionNavigation`, `ProgressHeader`).

## Critical Gaps Blocking the Full Slice

The frontend `quiz-sessions.ts` calls a Part A / Part B bulk-submit API (`/v1/api/test-sessions/`) that does not exist in the backend. The backend exposes a sequential per-question endpoint at `/v1/api/sessions/`. Nothing works end-to-end until this contract is aligned. Score finalization is also missing — a completed quiz session never writes its result back to `test_submissions`, so the trainer dashboard never sees a grade.

---

## 6 Prioritized Features for Days 11–15

The following features are listed in implementation order. Features 1 and 2 are gap-fixes against the Day 13–14 deliverables. Features 3–6 complete the Day 14–15 curriculum items and the vertical-slice deployment.

---

### 1. FE ↔ BE API Contract Alignment
*Rewire `quiz-sessions.ts` and the quiz page to use the actual backend session contract: one `POST /v1/api/sessions` to create a session, then one `POST /v1/api/sessions/{id}/answer` per question with an `Idempotency-Key` header.*

- **Curriculum Fit**: Day 13 (Dynamic routing with App Router parameters, authentication context propagation, client components for interactivity, multi-step UI navigation without state loss).
- **Prerequisites**: Day 13 topics. Backend session and answer endpoints must be healthy (already done).
- **Cross-Week Dependencies**: Requires the gateway route `^/v1/api/sessions(/.*)?$` already wired to `test-management-service` (confirmed in `api-gateway-service/main.py`). Requires `QuizSessionStartResponse` returning `session_token`, `server_now`, `expires_at`, and first `question` (already the case).
- **Required for**: Every other feature — the timer seeding (F3), RHF form (F4), autosave endpoint (F5), integration tests (F5), and Playwright E2E (F6) all depend on the FE driving the correct API shape.
- **Time Estimate**: Without AI tools: 4–6 hours | With AI tools: 2–3 hours
- **Implementation Details**:
  1. Delete or stub out the Part A / Part B functions in `frontend/src/lib/api/quiz-sessions.ts`. Replace with `createSession(testId, submissionId)` → `POST /v1/api/sessions`, `submitAnswer(sessionId, payload)` → `POST /v1/api/sessions/{id}/answer`.
  2. Update `frontend/src/lib/api/types.ts`: replace `TestSessionCreate`, `PartAQuestionsResponse`, etc. with `QuizSessionCreate`, `QuizSessionStartResponse`, and `AnswerSubmit` / `AnswerAck` shapes that mirror the backend Pydantic schemas exactly.
  3. Rewrite the session-init block in `QuizContent` (the client component in `page.tsx`): call `createSession`, store `session_token`, `server_now`, `expires_at`, and the first `question` from the response — do not call a separate questions endpoint.
  4. Replace the `handleSubmitPartA` / `handleFinalSubmit` dual-submit flow with a single `submitAnswer` call per question as the user advances, passing `session_token`, `question_id`, and `answers` plus a generated `Idempotency-Key` UUID header.
  5. On `AnswerAck.finished === true`, mark the quiz completed and redirect; the session is now `submitted` server-side with no separate "submit" call needed.

---

### 2. Score Finalization: Write Quiz Result to TestSubmission on Session Close
*Add a post-submit hook that aggregates `QuizAnswer.earned / possible`, writes `ai_score` and `percentage_score` to the matching `test_submissions` row, and transitions it to `COMPLETED`.*

- **Curriculum Fit**: Day 12 (State finalization and immutability patterns, cross-service state, deterministic scoring algorithms).
- **Prerequisites**: Day 12 topics. `QuizAnswerService.submit_answer` state machine and `TestSubmission` model must be in place (already done).
- **Cross-Week Dependencies**: Requires `test_submissions.ai_score` and `test_submissions.status` columns to exist (confirmed in `src/models/test_submission.py`). Requires `QuizAnswer` rows to be persisted before aggregation — happens in the same transaction in `submit_answer`.
- **Required for**: F3 (timer shows correct post-submit state), F6 (Playwright happy-path asserts a score in the completed-tests list), W4 results reporting endpoints.
- **Time Estimate**: Without AI tools: 3–5 hours | With AI tools: 1–2 hours
- **Implementation Details**:
  1. At the end of `QuizAnswerService.submit_answer`, after `session.status = SessionStatus.submitted`, call a new `_finalize_submission(db, session)` coroutine within the same transaction (before `db.commit()`).
  2. In `_finalize_submission`: query all `QuizAnswer` rows for `session.id`, sum `earned` and `possible`, compute `percentage = sum(earned) / sum(possible) * 100` (guard against `possible == 0`).
  3. If `session.submission_id` is set, load the `TestSubmission` row and update `ai_score = percentage`, `status = "COMPLETED"`, `submitted_at = now`. Use `SELECT FOR UPDATE` on the submission row to prevent a concurrent finalization race.
  4. If `session.submission_id` is `None`, log a warning and skip — do not raise, because a session without a linked submission is still valid for standalone testing.
  5. Add a unit test in `tests/test_quiz_session_answers.py`: mock `TestSubmissionRepository`, call `submit_answer` for the final question, assert `ai_score` and `status` were written; add an edge-case test for `possible == 0`.

---

### 3. Server-Anchored Timer with Submit-and-Lock UX
*Replace the `localStorage`-derived countdown with one seeded from `server_now` / `expires_at`, and freeze all UI controls the moment the final answer is confirmed by the server.*

- **Curriculum Fit**: Day 14 (Client timers anchored to server time, submit-and-lock UX flow, optimistic updates vs. server confirmation, graceful handling of network failures).
- **Prerequisites**: Day 14 topics. F1 must be complete — `server_now` and `expires_at` must reach the client from the session-create response.
- **Cross-Week Dependencies**: Requires `QuizSessionStartResponse.server_now` and `QuizSessionStartResponse.expires_at` (already returned). Requires F1 to pass those values into the component tree rather than a locally computed duration.
- **Required for**: F6 (Playwright asserts timer is visible and inputs are disabled post-submit).
- **Time Estimate**: Without AI tools: 4–7 hours | With AI tools: 2–3 hours
- **Implementation Details**:
  1. Rewrite `useTimer` in `frontend/src/lib/hooks/useTimer.ts`: accept `serverNow: string` (ISO) and `expiresAt: string` (ISO) instead of `durationSeconds`. On mount, compute `remainingMs = new Date(expiresAt).getTime() - (Date.now() - (Date.now() - new Date(serverNow).getTime()))`. Each tick: `remaining = Math.max(0, new Date(expiresAt).getTime() - Date.now())` — absolute subtraction, not a local counter.
  2. Remove all `localStorage` timer reads and writes from `useTimer`; the server is the source of truth and a page reload creates a new session.
  3. Add a `locked` boolean to `QuizContent` state (or promote to a `useReducer`). Set `locked = true` immediately when `AnswerAck.finished === true` is received — before any redirect or toast.
  4. Pass `locked` to `QuestionCard`, `QuestionNavigation`, and the submit button. When `locked`, render all inputs as `disabled` and the submit button as a spinner or "Submitted" label.
  5. On timer expiry, call the current question's `submitAnswer` automatically if not already locked; set `locked = true` before the call fires.
  6. Update `useTimer.test.ts`: replace duration-based tests with server-timestamp-based tests, asserting that a 5-second gap between `serverNow` and `expiresAt` produces ~5 seconds remaining at mount regardless of local clock offset.

---

### 4. react-hook-form + zod Schema for Quiz Answer Collection
*Replace the raw `Map<string, AnswerValue>` state with a `react-hook-form` form, add a `zod` schema that requires an answer for the current question before advancing, and wire the submit guard to zod's error state.*

- **Curriculum Fit**: Day 14 (Form state collection with react-hook-form, client-side validation with zod, React state management).
- **Prerequisites**: Day 14 topics. F1 must be complete (the form field names are `question_id` strings from the session response).
- **Cross-Week Dependencies**: No backend changes needed. Requires `react-hook-form` and `zod` to be present in `frontend/package.json` (both are already listed as dependencies via `shadcn/ui`).
- **Required for**: F6 (Playwright form interaction relies on stable input IDs that RHF names provide).
- **Time Estimate**: Without AI tools: 4–6 hours | With AI tools: 2–3 hours
- **Implementation Details**:
  1. In `QuizContent`, replace `const [answers, setAnswers] = useState<Map<...>>` with `const { register, handleSubmit, formState, setValue, getValues } = useForm<Record<string, AnswerValue>>()`.
  2. Define a `zod` schema: `z.record(z.string(), z.union([z.number(), z.array(z.number()), z.boolean()]))` with a `.refine` that checks the current question's `question_id` key is present and non-null before allowing navigation to the next question or submission.
  3. Register each question's answer field as `register(question.question_id)` inside `QuestionCard`; pass `setValue` down as the `onAnswerChange` callback.
  4. Replace `window.confirm` in `handleConfirmSubmit` with `handleSubmit(onValid, onInvalid)` — `onInvalid` shows a `toast.error` listing unanswered questions from `formState.errors`, `onValid` proceeds to call `submitAnswer`.
  5. Add `zod` resolver: `useForm({ resolver: zodResolver(quizAnswerSchema) })` so RHF runs schema validation on every submit attempt.
  6. Write a component test asserting that clicking Submit without selecting an answer does not call `submitAnswer` and renders a validation error.

---

### 5. Parametrized pytest Suite + Real-Container Integration Tests
*Add a parametrized scoring test file covering all edge cases, and add integration tests that exercise the `SELECT FOR UPDATE` race and unique-constraint guard against real Postgres and Mongo containers.*

- **Curriculum Fit**: Day 12 (AI-assisted test authoring with parametrized pytest cases), Day 15 (Integration testing against production-shaped data stores, database transactions and `SELECT FOR UPDATE`).
- **Prerequisites**: Day 15 topics. F2 must be complete. Pytest and `pytest-asyncio` must be configured in `test-management-service` (already the case).
- **Cross-Week Dependencies**: Requires a live Postgres container reachable in CI (GitHub Actions service containers). Requires `test-management-service/pytest.ini` to distinguish unit vs. integration marks. Requires the `quiz_answers` and `idempotency_keys` tables to be created via `create_all` or Alembic before integration tests run.
- **Required for**: F6 (smoke script runs after integration tests pass in CI).
- **Time Estimate**: Without AI tools: 6–10 hours | With AI tools: 3–5 hours
- **Implementation Details**:
  1. Create `tests/test_scoring_parametrized.py`. Use `@pytest.mark.parametrize` to cover: empty `correct_answers`, all-wrong single-select, partial multi-select overlap, exact multi-select match, `True`/`False` true-false variants, submitted with `answers=[]`, and `question_type="text"` (non-auto-scored zero-possible). Verify `ScoreResult.earned`, `is_correct`, and `details` for each case.
  2. Add a `@pytest.mark.integration` marker and a `conftest.py` fixture that provisions a real async SQLAlchemy engine against the CI Postgres service container, runs `Base.metadata.create_all`, and yields a `AsyncSession`.
  3. Write a session-creation integration test: insert a `Test` row, call `QuizSessionService.create_session` with a mocked question-service HTTP response, assert the returned `session_id` is a valid UUID and the `quiz_sessions` row exists with `expires_at > server_now`.
  4. Write a concurrency integration test: launch two `asyncio.gather` tasks both posting the same `question_id` + `Idempotency-Key` to the same session; assert exactly one returns `200` and one returns `409`, and `current_index` in Postgres advanced exactly once.
  5. Add a CI step to `.github/workflows/ci-pipeline.yml` that starts Postgres and Mongo service containers and runs `pytest -m integration --cov --cov-fail-under=70` after the unit test step.

---

### 6. Playwright End-to-End Happy-Path Test and Smoke Script
*Write a Playwright test that drives a real browser through login → session creation → answer all questions → submit, and wire it into CI behind a container-health smoke check.*

- **Curriculum Fit**: Day 15 (End-to-end smoke testing in the deployed environment, distributed log analysis across services, vertical-slice deployment, effective code review practice).
- **Prerequisites**: Day 15 topics. F1–F4 must be complete and the full Compose stack must be healthy. F5 smoke script pattern is reused as the pre-flight check.
- **Cross-Week Dependencies**: Requires a seeded participant user and an assigned test in Postgres (use `seed_db.py`). Requires Nginx or direct port-3000 access from the Playwright runner. Requires `pnpm dlx playwright install --with-deps chromium` to be added to the CI job.
- **Required for**: Day 15 deliverable "Full slice working & deployed".
- **Time Estimate**: Without AI tools: 5–8 hours | With AI tools: 2–4 hours
- **Implementation Details**:
  1. Add `playwright.config.ts` to `frontend/` pointing at `http://localhost:3000`, using the `chromium` project, with `baseURL` and a 30-second timeout.
  2. Create `frontend/tests/e2e/quiz-taking.spec.ts`. Happy path: navigate to `/`, fill login credentials for the seeded participant, assert redirect to `/participant/dashboard`, click **Start** on the first assigned test, answer each question via `page.locator('[data-testid="option-{n}"]').click()`, click **Submit Quiz**, and assert the page shows a disabled submit button and a "Quiz Submitted!" heading.
  3. Update `test-services.sh` to curl `/health` on every current Compose service (user-service `:8002`, test-management-service `:8001`, question-management-service `:8003`, api-gateway `:8000`, MinIO `:9001`) and exit non-zero on any non-200 — replacing the stale Consul/Lambda checks.
  4. Add a CI job `e2e` that depends on the build matrix, runs `docker compose up -d --wait`, executes `./test-services.sh`, then `pnpm exec playwright test`, and on failure uploads `docker compose logs --no-color` as a CI artifact for cross-service trace analysis.
  5. Add `data-testid` attributes to the answer option elements in `QuestionCard` so Playwright selectors are stable and independent of CSS class names.

---

## Suggested Work Order

1. F1 — rewire `quiz-sessions.ts` and quiz page to the real backend contract.
2. F2 — add `_finalize_submission` inside the existing answer-service transaction.
3. F3 — replace `localStorage` timer with server-timestamp anchor; add `locked` state.
4. F4 — drop in `react-hook-form` + `zod`; wire submit guard to schema errors.
5. F5 — parametrized scoring tests first (unit, fast), then real-Postgres integration tests.
6. F6 — Playwright happy-path after the full vertical slice passes locally against Compose.

## Security and Reliability Notes

- Never return `correct_answers` in any client-facing payload; `_strip_correct_answers` already enforces this — do not bypass it.
- Treat `session_token` as a secret: never log it, never put it in a URL parameter.
- Keep `Idempotency-Key` generation client-side (`crypto.randomUUID()`) so the same UUID is stable across retries of the same question but a new UUID is generated for each new question.
- Enforce `submitted` / `expired` immutability server-side regardless of client UI state — the `locked` flag in F3/F4 is UX only.
- Classify fetch errors before retrying: 409/410/422 are semantic and must not retry; 502/503/504 and network timeouts may retry with bounded exponential backoff.
