# W4 Candidate Results Demo Slice

> Branch: `jor-w4-candidate-results-page` (base `jorge-main`).
> Goal: ship the Day 16 candidate report endpoints + the Day 17 results page
> for the Week 4 demo, keeping the existing secure quiz finalization,
> reporting, and security/correctness fixes intact.

## Objective

A participant finishes a quiz and lands on a dedicated, deep-linkable results
page with a score chart; their dashboard average reflects auto-scored
(COMPLETED) quizzes; trainers/admins and the candidate themselves can read a
candidate report and a paginated, filterable, sortable attempt history.

## Changes

### Backend — `services/reporting-and-analytics-service`

- `src/utils/dependencies.py`
  - Added `require_self_or_privileged`: a participant may read **only their own**
    candidate report (`user_id` must match the gateway-verified `X-User-Id`);
    trainers/admins may read any. Other cases → 403 (never confirms another id).
  - Kept `require_trainer_or_admin` for the existing staff-only analytics.
- `src/schemas/report_schema.py`
  - Added `CandidateReport`, `AttemptEntry`, `PaginatedAttempts`. Existing
    `OverviewReport`/`TestReport`/`ParticipantReport` untouched.
- `src/v1/routes/report_route.py`
  - Added `GET /v1/api/reports/user/{user_id}` (candidate summary) and
    `GET /v1/api/reports/user/{user_id}/attempts` (page/page_size/status/sort/
    order). Score uses the shared `effective_score` (final → trainer → ai),
    unscored attempts excluded from the average. Existing trainer endpoints
    (`/overview`, `/tests/{id}`, `/participants/{id}`) left in place.
- `tests/test_reports.py`
  - Added coverage: auth header required, participant self-read allowed,
    participant-cannot-read-other (403), trainer-reads-any, score semantics +
    default `submitted_at` sort, status filter (case-insensitive), sort by
    score desc, and pagination.

The gateway already routes `/v1/api/reports(/.*)?` → reporting service, so no
gateway change was needed.

### Frontend — `frontend/src`

- `lib/api/reports.ts` (new) + `lib/api/index.ts`
  - Typed client + `CandidateReport`/`AttemptEntry`/`PaginatedAttempts` matching
    the final backend envelope; `getCandidateReport` / `getCandidateAttempts`.
- `app/(dashboard)/participant/tests/results/[sessionId]/`
  - `page.tsx` (new): re-reads the durable quiz session (refresh-/deep-link
    safe), renders the chart + score breakdown. No answer keys exposed.
  - `loading.tsx`, `error.tsx` (new): route-level skeleton + error boundary.
- `components/participant/ResultsChart.tsx`, `ResultsSkeleton.tsx` (new)
  - Correct/incorrect/unanswered donut + headline stats; loading placeholder.
- `app/(dashboard)/participant/tests/take/quiz/[testId]/page.tsx`
  - On successful (and 409-already-finalized) submit, redirect to
    `/participant/tests/results/{sessionId}`.
- Score visibility (COMPLETED + `final_score`, not only GRADED):
  - `lib/api/dashboard.ts` — participant average now counts COMPLETED + GRADED.
  - `app/(dashboard)/participant/tests/page.tsx` — average across COMPLETED +
    GRADED scored attempts.
  - `app/(dashboard)/participant/dashboard/page.tsx` — "Recent Results" includes
    COMPLETED; **start link fixed `/take/mcq` → `/take/quiz?submission=…`**.

## Verification

- `pytest services/reporting-and-analytics-service` → **31 passed**.
- `pytest` test-management finalization (`test_submission_finalize`,
  `test_quiz_session`, `test_quiz_session_answers`) → **19 passed**.
- `ruff check services/reporting-and-analytics-service` → clean.
- Frontend: `pnpm lint` (0 warnings), `pnpm test` (31 passed), `pnpm build` (ok;
  `/participant/tests/results/[sessionId]` route emitted).
- Manual demo smoke (documented in `Week4/demo-flow1.docx`): trainer assigns a
  quiz → participant submits → results page + chart render → dashboard shows the
  score. Run against `docker compose up --build`.

## Out of scope / not changed

- No removal of the legacy `/take/mcq/[testId]` page (no links point to it now).
- No changes to trainer reporting endpoints or quiz finalization logic.
