# W5-F1 — Free-text answer scoring & manual grading flow — Plan

**Feature:** [W5-F1 detail](../features/w5-f1-free-text-manual-grading.md)
**Spec origin:** trainer-defined remediation; deferred from
[W3-F2](../features/w3-f2-scoring-engine-locking.md) (scoring core punts non
auto-scorable types to a never-built "manual review (W4)").
**Depends on:** W3-F2 (scoring engine ✅), W4-F1 (results endpoints ✅), W4-F3
(trainer RBAC — `get_current_trainer` ✅).
**Unblocks:** complete grading for `text` questions; accurate participant/trainer
scores when a test contains free-text items.

## Locked decisions

- **No persisted session score.** W4-F1 (ADR 0001) computes attempt score
  on-read in the reporting service as `AVG(answers.score) * 100` over a session's
  answer rows (`report_repository.py:_session_score_subquery`). So grading a
  `text` answer is just an **UPDATE of that answer row** — the reporting AVG then
  reflects it with no recompute call. "Recompute session score on grade" is
  satisfied structurally by this read-time aggregation.
- **Pending answers are excluded from the provisional score**, not scored 0.0.
  A new `grading_status` column drives this: the reporting AVG filters out
  `PENDING_REVIEW` rows so an ungraded `text` answer does not silently drag the
  attempt to 0. Once graded, the row's `score` + `grading_status=GRADED` make it
  count.
- **`needs_grading`** is a real boolean column on `sessions`, set at finalize
  (any `PENDING_REVIEW` answer ⇒ true) and recomputed on each grade (false when
  no pending answers remain). Surfaced in the trainer queue and the reporting
  attempt row.
- **Endpoints live under the existing `/sessions` prefix** (session_route.py) →
  gateway `^/v1/api/sessions(/.*)?$` already covers them; **no new `ROUTES`
  entry**. The static queue path is registered before the `/{session_id}`
  dynamic route to avoid UUID-parse collision.
- **Manual `is_correct`** = `score >= 1.0`.

## Context — what exists now

- `scoring.score()` (`services/test-management-service/src/scoring/__init__.py:25-43`)
  dispatches `mcq`/`true_false`→exact, `multi`→partial; **any other type returns
  a hardcoded `ScoreResult(score=0.0, is_correct=False)`** — the bug.
- `ScoreResult` (`src/scoring/result.py`) = frozen dataclass `score`,
  `is_correct`, `max_score`.
- `submit_answer` (`src/services/session_service.py:265-308`) scores, persists an
  `Answer` row, advances the state machine, finalizes to `SUBMITTED` on the last
  slot. All in one txn under a `FOR UPDATE` lock + idempotency replay.
- `Answer` model (`src/models/answer.py`): `score` Float (non-null, default 0.0),
  `is_correct` Bool, `submitted_answers` JSON, unique `(session_id,
  question_index)`. No grading-status / feedback fields.
- `Session` model (`src/models/session.py`): `status` enum
  (ACTIVE/SUBMITTED/EXPIRED), `submitted_at`; **no score column, no
  needs_grading**.
- Trainer RBAC: `get_current_trainer` (`src/utils/dependencies.py:63`), used as a
  FastAPI `Depends`. Example: `test_submission_route.py:93`.
- Reporting service reads `answers`/`sessions` **read-only** via mapped copies on
  `TmsBase` (`reporting-and-analytics-service/src/models/tms_readonly.py`); the
  per-session score subquery is `report_repository.py:_session_score_subquery`
  (`AVG(TmsAnswer.score)*100`). `TmsAnswer` maps only the columns it reads.
- TMS schema is **Alembic-owned** (head = `0007`). Reporting owns no TMS tables
  (ADR 0001) — its read-only mappings are added to `TmsBase` only.
- Both `test-management-service/tests/` and
  `reporting-and-analytics-service/tests/` exist (pytest + a sqlite-backed
  fixture for the reporting read-only tables).
- Frontend trainer area: pages under `frontend/src/app/(dashboard)/trainer/`
  ({dashboard,questions,tests}); components in `src/components/trainer/`; generic
  BFF proxy `src/app/api/v1/[...path]/route.ts` already forwards any
  `/v1/api/...` call (no per-route BFF needed).

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W5F1`** off `richardh` before any code change; confirm
  with `git branch --show-current`.
- **First commit = this plan file.**
- One commit per milestone (Conventional Commits).

## Milestones

### M1 — Scoring core: signal "pending review" for non-auto-scorable types
Files: `src/scoring/result.py`, `src/scoring/__init__.py`, `tests/test_scoring.py`.
- Add `requires_review: bool = False` to `ScoreResult`.
- `score()`: for an unknown/`text` type return
  `ScoreResult(score=0.0, is_correct=False, requires_review=True)` (drop the
  misleading "manual review (W4)" comment, point at W5-F1).
- Unit tests: `text` → `requires_review=True`, `score=0.0`; `mcq`/`true_false`/
  `multi` unchanged (`requires_review` stays False — regression guard).
- **Commit:** `feat(scoring): flag non-auto-scorable answers for manual review`.

### M2 — Answer/Session model + Alembic 0008 + finalize semantics
Files: `src/models/answer.py`, `src/models/session.py`,
`alembic/versions/0008_*.py`, `src/services/session_service.py`.
- `Answer`: add `grading_status` (Enum `AUTO|PENDING_REVIEW|GRADED`, non-null,
  default `AUTO`), `feedback` (Text, nullable), `graded_by_id` (Integer,
  nullable), `graded_at` (DateTime, nullable).
- `Session`: add `needs_grading` (Boolean, non-null, server default false).
- Define a `GradingStatus` enum (new `src/models/` enum or alongside Answer);
  mirror in reporting (M4).
- `alembic revision --autogenerate -m "add answer grading status + session
  needs_grading (W5-F1)"` → review/adjust to `0008` (down_revision `0007`);
  ensure enum type + server defaults render; backfill existing rows
  (`grading_status='AUTO'`, `needs_grading=false`).
- `submit_answer`: map `result.requires_review` →
  `grading_status=PENDING_REVIEW` (else `AUTO`); on finalize set
  `session.needs_grading = True` if **any** answer for the session is
  `PENDING_REVIEW` (query the just-written rows), else False. Auto-only sessions
  → `needs_grading=False` (regression guard).
- **Commit:** `feat(grading): persist pending-review state + needs_grading (migration 0008)`.

### M3 — Trainer grade endpoint + "to grade" queue
Files: `src/schemas/grading_schema.py` (new), `src/repositories/answer_repository.py`,
`src/services/grading_service.py` (new), `src/v1/routes/session_route.py`,
`main.py` (router include if a new router is used — else extend session_route).
- Schemas: `GradeRequest` (`score: float` 0..1 validated, `feedback: str | None`),
  `GradedAnswerOut`, `PendingAnswerOut`, `GradingQueueOut`
  (`{items, total, page, size}` to match the W4 envelope).
- Repository: `get_pending(db, test_id?, page, size)`, `get_answer(db, id)`,
  `count_pending_for_session(db, session_id)`.
- Service `grade_answer`: load answer; reject if not `PENDING_REVIEW`/`GRADED`
  (409 on a non-text/auto answer); set `score`, `is_correct = score>=1.0`,
  `feedback`, `graded_by_id` (X-User-Id), `graded_at`,
  `grading_status=GRADED`; recompute `session.needs_grading`
  (false when `count_pending_for_session == 0`); commit.
- Routes (all `Depends(get_current_trainer)`):
  - `GET /sessions/grading-queue?test_id=&page=&size=` → pending answers (joined
    to session/test/question metadata). **Register before** the `/{session_id}`
    dynamic route.
  - `POST /sessions/{session_id}/answers/{question_index}/grade` → grade one
    answer; 404 unknown, 409 not-pending, 200 graded.
- RBAC: 401 (no/invalid headers) / 403 (non-trainer) inherited from
  `get_current_trainer`.
- Gateway: covered by existing `/sessions` pattern — **no ROUTES change**
  (note in requirements review).
- **Commit:** `feat(grading): trainer grade endpoint + to-grade queue (RBAC-gated)`.

### M4 — Reporting: exclude pending from provisional score
Files: `reporting-and-analytics-service/src/models/tms_readonly.py`,
`src/repositories/report_repository.py`, `src/schemas/report_schema.py`.
- `TmsAnswer`: add `grading_status` (portable `String`/`Enum`, matching the TMS
  column) — read-only mapping only, no DDL (ADR 0001 containment).
- `TmsSession`: add `needs_grading` (Boolean) read-only mapping.
- `_session_score_subquery`: change `AVG(TmsAnswer.score)` to
  `AVG(score) FILTER (WHERE grading_status != 'PENDING_REVIEW')` (or
  `case`-guarded avg) so pending answers are excluded from the provisional
  attempt score. A session with only ungraded text answers → score `NULL`
  (correctly "no score yet"), not 0.
- Expose `needs_grading` on the attempt row in `GET
  /reports/user/{id}/attempts` (`report_schema.py` + the attempts query) so the
  results page (W4-F2) can mark a score provisional.
- **Commit:** `feat(reporting): exclude pending-review answers from attempt score`.

### M5 — Frontend trainer grader surface
Files: `frontend/src/app/(dashboard)/trainer/grading/page.tsx` (new),
`src/components/trainer/GradingQueue.tsx` + `GradeAnswerSheet.tsx` (new),
`src/lib/api/` client call (reuse generic BFF proxy).
- Page: trainer-only (middleware already gates `/trainer/*`); fetch
  `GET /v1/api/sessions/grading-queue`, list pending answers (test name,
  participant, question prompt, submitted text).
- Grade sheet: show the pending `text` answer + question prompt/sample answer;
  submit `score` (0..1, simple input/slider) + optional `feedback` via
  `POST /v1/api/sessions/{id}/answers/{index}/grade`; on success refresh the
  queue. Reuse shadcn Sheet/form conventions from existing
  `SubmissionReviewSheet.tsx`.
- **Commit:** `feat(frontend): trainer grading queue + grade-answer surface`.

### M6 — Tests
Files: `test-management-service/tests/` (+ `integration/`),
`reporting-and-analytics-service/tests/`,
`frontend/src/components/trainer/__tests__/`.
- TMS unit: scoring dispatch already in M1; `grading_service.grade_answer`
  recompute + `needs_grading` flip; not-pending → 409.
- TMS integration: submit a mix of auto + `text` answers → session finalizes
  `SUBMITTED` with `needs_grading=True` and the text answer `PENDING_REVIEW`;
  grade it → `needs_grading=False`, score updated. Auto-only session →
  `needs_grading=False` (regression).
- Grade endpoint RBAC: 401 (no headers) / 403 (participant) / 200 (trainer).
- Reporting: attempt with a pending text answer → provisional score excludes it;
  after grade the AVG includes it. (sqlite fixture — add `grading_status` to the
  fixture rows.)
- Frontend: grader renders a pending answer + submits a score (mock fetch).
- **Commit:** `test(grading): scoring/finalize/grade RBAC + reporting exclusion`.

## Testing & validation

- TMS: `cd services/test-management-service && pytest --cov` — all green,
  including new scoring/grading/finalize tests.
- Reporting: `cd services/reporting-and-analytics-service && pytest --cov` — green,
  including the pending-exclusion test.
- Frontend: `cd frontend && pnpm lint && pnpm build` clean; `pnpm test
  --if-present` for the new grader test.
- Migration: `alembic upgrade head` applies `0008` cleanly on a fresh
  `eval_ai_dev`; `alembic downgrade -1` reverts.
- Smoke (`docker compose up --build`): submit a session containing a `text`
  question → answer recorded `PENDING_REVIEW`, session `needs_grading=true`,
  reporting attempt score excludes it; trainer hits the queue, grades it; score
  appears.
- **Pass bar:** every Step in the detail doc satisfied, all listed test commands
  green, no `ROUTES`/gateway regression.

## Requirements review (final milestone)

Re-read the W5-F1 detail Steps + Acceptance against the diff:
1. Pending-review state persisted (not 0.0) — `Answer.grading_status`, migration
   0008, `submit_answer` mapping.
2. Finalize semantics — `session.needs_grading`, provisional score = reporting
   AVG excluding pending; auto-only regression-guarded.
3. Trainer grade endpoint — RBAC-gated POST, recompute on grade.
4. To-grade queue — RBAC-gated GET with `test_id` filter.
5. Frontend grader surface.
6. Tests green across all three layers.
Cite file:line + commit for each. Then check off the detail-doc Steps with
evidence and flip the `FEATURE_STATUS.md` W5-F1 row to ✅; commit those doc
updates on the branch.

## Push gate

Push `richardh-feat-W5F1` to origin **only if** all test commands above are green
**and** every detail-doc Step is confirmed. Otherwise stop, keep the branch
local, report what's outstanding. After push, best-effort KG re-ingest
(`kg.py up && kg.py ingest && kg.py down`); skip + note if Docker/models
unavailable.
