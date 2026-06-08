# Week 3 Feature Implementation Plan

## Purpose

This handoff document lets Claude Code or another coding agent implement the selected Week 3 work without re-analyzing the entire repository.

Source inputs reviewed:

- `D:\_Revature\Week3\days_11_15_features.md`
- Current `D:\_Revature\rev-eval` repo structure on branch `jorge-logging`


## Current Project Status Snapshot

### Already Present or Recently Implemented

- Nginx reverse proxy exists at `nginx/nginx.conf`, routing `/` and `/_next/` to the frontend and `/api/v1/` to the API gateway.
- Local TLS is already part of the Nginx compose mount through `nginx/certs`.
- Docker Compose already includes frontend, API gateway, user-service, test-management-service, question-management-service, Postgres, MongoDB, MinIO, and Nginx.
- Centralized logging work has been implemented locally in this branch:
  - `loki`, `grafana`, and `alloy` services in `docker-compose.yml`
  - `observability/` configs for Loki, Alloy, and Grafana provisioning
  - Python JSON logging helpers in each service
  - Nginx JSON access logs
  - Documentation at `docs/observability-logging.md`
- Backend pytest scaffolding exists for services.
- CI already includes Ruff, pytest coverage threshold, frontend lint/build/test, Docker builds, and Trivy scans.
- Frontend has an existing participant MCQ-taking page at:
  - `frontend/src/app/(dashboard)/participant/tests/take/mcq/[testId]/page.tsx`
- Frontend has quiz-session API helpers at:
  - `frontend/src/lib/api/quiz-sessions.ts`
- Existing frontend quiz APIs call endpoints like:
  - `POST /v1/api/test-sessions/`
  - `GET /v1/api/test-sessions/{sessionId}/part-a/questions`
  - `POST /v1/api/test-sessions/{sessionId}/part-a/submit`
  - `GET /v1/api/test-sessions/{sessionId}/part-b/questions`
  - `POST /v1/api/test-sessions/{sessionId}/part-b/submit`
- `test-services.sh` exists but appears stale; it checks Consul and a Lambda-style service that are not present in the current Compose topology.

### Current Gaps Against Days 11-15

- The Day 11-15 milestone expects a server-authoritative session model with UUID session IDs, server_now/expires_at, locking, idempotency, draft autosave, and full test-taking UX.
- Current test-management-service has `TestSubmission` models and services, but no obvious Day 11 `sessions` table/model with `server_now`, `expires_at`, `current_index`, `status`, idempotency, and draft support.
- The existing frontend test-taking page is client-heavy and appears to create sessions after client load. The Day 13 target asks for server-side session minting in a dynamic route with initial question data passed to a client runner.
- Playwright is present in lockfile metadata, but there is no obvious Playwright config or E2E test suite in the repo.

## Four Priority Features for Week 3

Selected implementation order:

### 1. Quiz Session Creation Backend
- This is the foundation for the rest of the quiz-taking slice.
- Scoring, locking, autosave, frontend session loading, and result finalization all depend on a durable server-side session row.
- The repo already has SQLAlchemy async infrastructure in `test-management-service`, plus cross-service HTTP patterns through `httpx`, so this is feasible without first reorganizing the app.
- It replaces fragile client-derived timing with server-authoritative `server_now` and `expires_at`.

### 2. Scoring Engine with Exact-Match and Partial-Credit Algorithms
- Once sessions exist, the next highest-value backend feature is deterministic scoring plus answer mutation safety.
- Pure scoring functions are small, easy to unit test, and low risk.
- Pessimistic locking and idempotency are necessary before autosave, submit-lock UX, and E2E tests can be trusted.
- This directly supports Day 12 curriculum topics and gives the frontend a reliable answer-submission contract.

### 3. Test-Taking Frontend Skeleton with Dynamic Routing and Auth Context
- The repo already has a participant MCQ-taking page and quiz API client helpers, so this feature can reuse and refactor existing work rather than start from zero.
- It should follow the backend session contract created in features 1 and 2.
- It unlocks the visible candidate workflow: start a test, render questions, navigate, and preserve answers.
- It should use the existing `/api/v1/[...path]` frontend proxy pattern and avoid exposing auth cookies to client bundles.

### 4. Auto-Saving Exam Client with Server-Anchored Timer and Submit-Lock UX
- This is the natural extension of the frontend runner after session creation, scoring, and navigation exist.
- It completes the user-facing Day 14 behavior: timer, draft safety, submit lock, and network failure handling.
- It should not be implemented before the backend state machine and draft endpoint exist.
- It improves reliability for the candidate experience before spending time on broader integration/E2E automation.


### Low Priority (Deferred):

**4. Integration Tests Against Real Postgres and Mongo Containers.**

**5. Playwright End-to-End Happy-Path Test and Smoke Script.**

    - They are valuable, but they test a workflow that does not fully exist yet.
    - The current `test-services.sh` is stale and should be updated after the actual session/scoring/autosave endpoints are settled.
    - Playwright would be brittle before route contracts, seeded data, auth flow, and submit-lock behavior are stable.
    - Add these as the next batch after the vertical slice works locally.

## Implementation Plan

### Feature 1: Quiz Session Creation Backend

Goal:

Implement a server-authoritative quiz session backend in `test-management-service`.

Primary files to add/update:

- `services/test-management-service/src/models/quiz_session.py`
- `services/test-management-service/src/models/quiz_answer.py`
- `services/test-management-service/src/repositories/quiz_session_repository.py`
- `services/test-management-service/src/repositories/quiz_answer_repository.py`
- `services/test-management-service/src/schemas/quiz_session_schema.py`
- `services/test-management-service/src/services/quiz_session_service.py`
- `services/test-management-service/src/v1/routes/quiz_session_route.py`
- `services/test-management-service/main.py`
- Alembic migration under `services/test-management-service/alembic/versions/` if Alembic is active in the repo
- If no Alembic workflow is reliable yet, update `services/test-management-service/src/db/session.py` init flow cautiously and document the gap

Suggested data model:

```text
quiz_sessions
- id: integer primary key or UUID primary key depending local convention
- session_id: UUID unique, public opaque ID
- test_id: integer FK to tests.id
- submission_id: integer nullable FK to test_submissions.id
- user_id: integer
- session_token: string unique, opaque secret
- status: enum/string: created | in_progress | submitted | expired
- current_index: integer default 0
- server_started_at: timestamptz
- expires_at: timestamptz
- submitted_at: timestamptz nullable
- created_at: timestamptz
- updated_at: timestamptz
```

```text
quiz_session_questions
- id
- session_id / quiz_session_id
- question_id: string Mongo ObjectId
- question_index: integer
- question_type: string
- snapshot_json: JSON
```

Implementation steps:

1. Confirm current test model has `duration_seconds` and use that for `expires_at`.
2. Add session and session-question models.
3. Add Pydantic schemas:
   - `QuizSessionCreate`
   - `QuizSessionStartResponse`
   - `QuizQuestionOut`
4. Add route:
   - `POST /v1/api/sessions`
   - Accept `test_id` and optional `submission_id`.
   - Derive `user_id` from auth context if available; otherwise keep current user extraction pattern consistent with existing routes.
5. Generate `session_id` with `uuid.uuid4()` and `session_token` with `secrets.token_urlsafe(32)`.
6. Compute `server_now = datetime.now(timezone.utc)` and `expires_at = server_now + duration_seconds`.
7. Persist the session before calling downstream services.
8. Use `httpx.AsyncClient` with explicit timeout to call question-management-service.
9. Propagate `X-Request-ID` or `X-Correlation-Id` from incoming request to outbound calls.
10. Fetch/select first question and save a question snapshot in Postgres.
11. Return:

```json
{
  "session_id": "uuid",
  "session_token": "opaque",
  "server_now": "iso timestamp",
  "expires_at": "iso timestamp",
  "status": "in_progress",
  "current_index": 0,
  "question": {
    "question_id": "mongo id",
    "question_type": "mcq",
    "question_text": "...",
    "options": []
  }
}
```

Testing:

- Unit test session expiry calculation.
- Route test with mocked question-management-service HTTP call.
- Test missing test returns 404.
- Test empty question pool returns a clear 503 or 424 style error.

Acceptance criteria:

- `POST /v1/api/sessions` creates a durable row with server-owned timing.
- Response includes first question without correct answers.
- Outbound call has timeout and correlation/request ID propagation.

### Feature 2: Scoring Engine with Exact-Match and Partial-Credit Algorithms

Goal:

Add deterministic scoring and safe answer submission.

Primary files to add/update:

- `services/test-management-service/src/scoring/__init__.py`
- `services/test-management-service/src/scoring/types.py`
- `services/test-management-service/src/scoring/exact_match.py`
- `services/test-management-service/src/scoring/partial_credit.py`
- `services/test-management-service/src/services/quiz_answer_service.py`
- `services/test-management-service/src/v1/routes/quiz_session_route.py`
- `services/test-management-service/src/models/idempotency_key.py`
- `services/test-management-service/tests/test_scoring.py`
- `services/test-management-service/tests/test_quiz_session_answers.py`

Scoring contract:

```python
score_question(
    question_type: str,
    correct_answers: list[int | str | bool],
    submitted_answers: list[int | str | bool],
) -> ScoreResult
```

Suggested `ScoreResult`:

```python
@dataclass(frozen=True)
class ScoreResult:
    earned: float
    possible: float
    is_correct: bool
    details: dict[str, Any]
```

Algorithm guidance:

- Single-select / true-false:
  - exact match only
  - `earned = 1.0` if submitted equals correct, otherwise `0.0`
- Multi-select:
  - partial credit using set overlap
  - preferred: `max(0, true_positives - false_positives) / len(correct_set)`
  - cap between `0.0` and `1.0`
  - record detail counts for auditability

Endpoint:

```text
POST /v1/api/sessions/{session_id}/answer
Headers:
  Idempotency-Key: required for mutation safety
Body:
  {
    "session_token": "opaque",
    "question_id": "mongo id",
    "answers": [1, 3]
  }
```

Implementation steps:

1. Create pure scoring module and unit tests before route wiring.
2. Add idempotency storage:
   - key
   - session_id
   - request_hash
   - response_json
   - created_at
3. In answer endpoint, require `Idempotency-Key`.
4. Start DB transaction.
5. Lock session row with `SELECT ... FOR UPDATE`.
6. Reject if session status is `submitted` or `expired`.
7. Reject if `expires_at <= now`; transition to `expired`.
8. Check idempotency table:
   - same key + same request returns prior response
   - same key + different request returns 409
9. Score answer using question snapshot/correct-answer lookup.
10. Persist answer row.
11. Advance `current_index`.
12. If final question reached, transition to `submitted` and set `submitted_at`.
13. Store idempotency response and return it.

Testing:

- Parameterized exact-match tests.
- Parameterized multi-select partial-credit tests.
- Duplicate idempotency key returns same response without double mutation.
- Submitted session rejects further answers with 409.
- Expired session rejects mutation and records expired status.

Acceptance criteria:

- Scoring functions are pure and pass unit tests.
- Answer mutation is transactionally safe.
- Idempotent retries do not double-score.
- Session state machine is enforced.

### Feature 3: Test-Taking Frontend Skeleton with Dynamic Routing and Auth Context

Goal:

Refactor or add a modern test-taking route that mints the session server-side and hands initial state to a client runner.

Primary files to add/update:

- Prefer new route:
  - `frontend/src/app/(dashboard)/participant/tests/take/[testId]/page.tsx`
- Existing route to evaluate/refactor:
  - `frontend/src/app/(dashboard)/participant/tests/take/mcq/[testId]/page.tsx`
- New components:
  - `frontend/src/components/quiz/TestRunner.tsx`
  - `frontend/src/components/quiz/SingleSelectQuestion.tsx`
  - `frontend/src/components/quiz/MultiSelectQuestion.tsx`
- Existing components to reuse if suitable:
  - `frontend/src/components/quiz/MCQQuestion.tsx`
  - `frontend/src/components/quiz/MultiQuestion.tsx`
  - `frontend/src/components/quiz/QuestionNavigation.tsx`
  - `frontend/src/components/quiz/ProgressHeader.tsx`
- API helpers:
  - `frontend/src/lib/api/quiz-sessions.ts`
  - `frontend/src/lib/api/types.ts`
- Session/auth helpers:
  - `frontend/src/lib/session.ts`
  - `frontend/src/app/api/v1/[...path]/route.ts`

Implementation steps:

1. Decide whether to replace the existing `take/mcq/[testId]` route or create the Day 13 generic `take/[testId]` route.
2. Implement server component page:
   - read auth session with existing `getSession()`
   - call backend `POST /v1/api/sessions` server-side
   - include auth token on backend call from server only
   - pass session response to `TestRunner`
3. Implement `TestRunner` as a client component with:
   - `currentIndex`
   - `answers` as `Map<string, unknown[]>`
   - `session`
   - `questions`
4. Implement one dispatch function:

```tsx
function renderQuestion(question) {
  switch (question.question_type) {
    case "mcq":
    case "true_false":
      return <SingleSelectQuestion ... />;
    case "multi":
      return <MultiSelectQuestion ... />;
    default:
      return <UnsupportedQuestion ... />;
  }
}
```

5. Keep Previous/Next navigation in React state only.
6. Preserve selections in the `Map`.
7. Submit each answer through the Day 12 answer endpoint with an `Idempotency-Key`.
8. Do not expose raw cookies or bearer tokens in the client component.

Testing:

- Component tests for question dispatch.
- Component tests for navigation preserving answers.
- Route smoke test through existing Next.js test setup if available.

Acceptance criteria:

- First question renders from server-provided data without client loading flicker.
- Single-select and multi-select render through one dispatch point.
- Back/forward navigation preserves answers.
- Auth token/cookie stays server-side.

### Feature 4: Auto-Saving Exam Client with Server-Anchored Timer and Submit-Lock UX

Goal:

Add timer, draft autosave, semantic/transient error handling, and immediate submit-lock behavior.

Primary files to add/update:

- Backend:
  - `services/test-management-service/src/v1/routes/quiz_session_route.py`
  - `services/test-management-service/src/services/quiz_session_service.py`
  - `services/test-management-service/src/models/quiz_draft.py` or draft JSON column/table
  - `services/test-management-service/src/schemas/quiz_session_schema.py`
- Frontend:
  - `frontend/src/components/quiz/TestRunner.tsx`
  - `frontend/src/lib/api/quiz-sessions.ts`
  - `frontend/src/lib/hooks/useTimer.ts`
  - `frontend/src/lib/hooks/useTimer.test.ts`
  - optional `frontend/src/lib/hooks/useAutosave.ts`
  - optional `frontend/src/lib/hooks/useAutosave.test.ts`

Backend endpoint:

```text
PATCH /v1/api/sessions/{session_id}/draft
Body:
  {
    "session_token": "opaque",
    "answers": {
      "question_id_1": [1],
      "question_id_2": [2, 4]
    }
  }
```

Submit endpoint:

```text
POST /v1/api/sessions/{session_id}/submit
Body:
  {
    "session_token": "opaque"
  }
```

Timer algorithm:

```text
remaining = (expires_at - server_now) - (Date.now() - mounted_at)
```

Implementation steps:

1. Add draft persistence endpoint that does not score and does not advance `current_index`.
2. Reject draft updates if session is `submitted` or `expired`.
3. Add submit endpoint that locks the session and transitions to `submitted`.
4. In `TestRunner`, use reducer state:
   - `idle`
   - `answering`
   - `autosaving`
   - `submitting`
   - `locked`
   - `error`
5. Compute timer from server timing values and mount time.
6. Autosave every 30 seconds or after answer changes with debounce.
7. Classify errors:
   - transient: network, 502, 503, 504 -> retry with backoff
   - semantic: 409, 410, 422 -> show message and stop retries
8. On submit click:
   - set `isLocked = true` immediately
   - disable all inputs and navigation that mutates answers
   - stop timer
   - send submit request
   - keep locked even if response is slow
9. On timer expiry, call submit automatically.

Testing:

- Timer hook test for server/client clock skew.
- Autosave debounce test.
- Locked-state rendering test.
- Backend draft endpoint rejects submitted/expired sessions.

Acceptance criteria:

- Timer uses server timing, not raw client clock.
- Answers autosave without advancing/scoring.
- Submit locks UI immediately.
- Expired/submitted sessions cannot mutate.
- Transient errors retry; semantic errors do not retry.

## Suggested Work Order for Coding Agent

1. Create a small backend design note or ADR for session state machine and scoring algorithm.
2. Implement Feature 1 model/schema/repository/service/route.
3. Add tests for Feature 1.
4. Implement Feature 2 scoring module and tests.
5. Wire answer endpoint, idempotency, and locking.
6. Add tests for Feature 2.
7. Refactor/add frontend route and `TestRunner` for Feature 3.
8. Add component tests for Feature 3.
9. Add draft/submit backend endpoints for Feature 4.
10. Add timer/autosave/submit-lock UX for Feature 4.
11. Add component and route tests for Feature 4.
12. Only after all four pass, start planning real DB integration tests and Playwright E2E.

## Testing Strategy

### Backend Unit Tests

Run from service folder:

```bash
cd services/test-management-service
pytest
```

Priority tests:

- scoring exact match
- scoring partial credit
- session creation schema
- session expiry computation
- idempotency behavior
- state-machine rejections

### Frontend Unit Tests

Run from frontend folder:

```bash
cd frontend
pnpm test --if-present
```

Priority tests:

- render dispatch by question type
- navigation preserves answer state
- timer skew calculation
- autosave debounce
- submit locked state disables inputs

### Compose Smoke

Use after backend endpoints exist:

```bash
docker compose config
docker compose up -d --build
curl -k https://localhost
curl -k https://localhost/api/v1/health
docker compose logs --no-color api-gateway test-management-service question-management-service
```

Update `test-services.sh` before relying on it because it currently references services that do not match the current Compose file.

## Files and Areas to Avoid Unless Needed

- Avoid broad refactors in trainer dashboards and unrelated UI components.
- Avoid changing CI gates unless a new test command requires it.
- Avoid replacing the existing frontend API client wholesale; extend `quiz-sessions.ts`.
- Avoid introducing a new auth pattern; use existing `frontend/src/lib/session.ts` and API proxy patterns.
- Avoid logging correct answers or session tokens.

## Security and Reliability Notes

- Treat `session_token` as a secret. Do not place it in URLs or logs.
- Do not return correct answers in question payloads.
- Use `X-Request-ID` or `X-Correlation-Id` for cross-service calls.
- Use explicit `httpx` timeouts.
- Keep retry counts bounded.
- Use low-cardinality log labels only; put dynamic IDs inside JSON log fields, not Loki labels.
- Enforce submitted/expired immutability on the backend even if the frontend disables controls.

## Manual Commit Recommendation

When implementing these features later, use focused commits:

```bash
git add services/test-management-service
git commit -m "Add quiz session creation backend"

git add services/test-management-service
git commit -m "Add quiz scoring and answer locking"

git add frontend/src/app frontend/src/components/quiz frontend/src/lib/api
git commit -m "Add server-minted quiz taking flow"

git add frontend/src services/test-management-service
git commit -m "Add quiz timer autosave and submit lock"
```

Because this branch currently has a broad dirty working tree, avoid `git add .`. Stage only files related to the feature being committed.

## Next Batch After These Four

After features 1-4 are stable:

1. Add integration tests against real Postgres and Mongo containers.
2. Update `test-services.sh` to match current Compose services.
3. Add Playwright config and a full quiz-taking happy-path test.
4. Add CI job that runs smoke checks, then Playwright, then uploads Compose logs as artifacts.
