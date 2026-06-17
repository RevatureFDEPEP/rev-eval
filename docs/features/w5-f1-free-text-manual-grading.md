# W5-F1 — Free-text answer scoring & manual grading flow

**Status:** ✅ Completed
**Spec:** trainer-defined remediation (non-catalog). Origin: deferred from
[W3-F2](w3-f2-scoring-engine-locking.md). The scoring core punts non-auto-scorable
question types to "manual review (W4)", but that grading flow was never built.
**Depends on:** W3-F2 (scoring engine), W4-F1 (results endpoints), W4-F3 (trainer RBAC).
**Unblocks:** complete grading for `text` questions; accurate participant/trainer
scores when a test contains free-text items.
**Last updated:** 2026-06-17

## Problem

`score()` only auto-scores `mcq`/`true_false` (exact match) and `multi` (Jaccard).
Any other type — notably free-text `text` — falls through to a hardcoded
`ScoreResult(score=0.0, is_correct=False)` "awaiting manual review (W4)":

```
services/test-management-service/src/scoring/__init__.py:33-43
```

No manual-grade endpoint, grader UI, or "pending review" state exists. So a `text`
answer is **permanently 0.0** — silently wrong, not flagged. Confirmed open at
program end (`docs/plans/w4-f5-tech-debt-audit-adrs.md:116`). The feature doc that
deferred it: `docs/features/w3-f2-scoring-engine-locking.md:70`.

> **Status: ✅ Completed** on branch `richardh-feat-W5F1`
> (plan: [w5-f1 plan](../plans/w5-f1-free-text-manual-grading.md)). Tests:
> TMS 112 passed / 6 skipped, reporting 46 passed, frontend 156 passed,
> lint 0 errors + build OK.

## Steps

- [x] **1. Persist a "pending manual review" state** — `GradingStatus`
      (`AUTO`|`PENDING_REVIEW`|`GRADED`) + grade payload columns on the answer
      model (`src/models/answer.py:18-46`); a `text` answer lands
      `PENDING_REVIEW` (`src/services/session_service.py:285-296`), excluded
      from the on-read score (M4). Alembic `0008`
      (`alembic/versions/0008_add_answer_grading_status_and_needs_grading.py`).
- [x] **2. Session finalize semantics** — `Session.needs_grading`
      (`src/models/session.py:45-51`) set at finalize when any answer is
      `PENDING_REVIEW` (`session_service.py:300-309`); the attempt's provisional
      score is the reporting AVG over non-pending answers (M4). Auto-only
      sessions stay `needs_grading=False` — regression-guarded
      (`tests/test_answer_endpoint.py::test_auto_only_session_does_not_need_grading`).
- [x] **3. Trainer grade endpoint** — `POST
      /v1/api/sessions/{id}/answers/{index}/grade`, TRAINER-gated
      (`get_current_trainer`), score 0..1 + feedback, recomputes `needs_grading`
      (`src/v1/routes/session_route.py:66-100`,
      `src/services/grading_service.py:79-127`). No `ROUTES` change — covered by
      the existing `^/v1/api/sessions(/.*)?$` pattern. The "session score
      recompute" is the reporting on-read AVG, so no score column to update.
- [x] **4. Trainer "to grade" queue** — `GET /v1/api/sessions/grading-queue`
      (`?test_id` filter, paginated), TRAINER-gated, enriched with question
      prompt + sample answer (`session_route.py:43-60`,
      `grading_service.py:38-77`, `AnswerRepository.list_pending`).
- [x] **5. Frontend grader surface** — `/trainer/grading` page
      (`frontend/src/app/(dashboard)/trainer/grading/page.tsx`) +
      `GradeAnswerSheet` (`frontend/src/components/trainer/GradeAnswerSheet.tsx`)
      + `grading` API module (`frontend/src/lib/api/grading.ts`).
- [x] **6. Tests** — scoring `text`→PENDING unit (`tests/test_scoring.py`);
      finalize auto+text (`tests/test_answer_endpoint.py`); grade service
      recompute/409 (`tests/test_grading_service.py`); grade endpoint RBAC
      401/403/200 (`tests/test_grade_endpoint.py`); reporting pending-exclusion
      (`reporting…/tests/test_grading_exclusion.py`); frontend grader render +
      submit (`…/__tests__/GradeAnswerSheet.test.tsx`).

## Out of scope

- Auto-grading `text` via NLP/LLM similarity — manual grading only here.
- Rubric/partial-rubric grading models beyond a single 0..1 score + feedback.

## Acceptance

- [x] A `text` answer is recorded `PENDING_REVIEW`, never a silent `0.0`.
- [x] A trainer can grade it; the attempt score recomputes (reporting on-read
      AVG now includes the graded answer); participant results (W4-F2) reflect
      the graded score and expose `needs_grading` while provisional.
- [x] Tests above green; `FEATURE_STATUS.md` row flipped to ✅ with evidence.
