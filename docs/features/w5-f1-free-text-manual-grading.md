# W5-F1 — Free-text answer scoring & manual grading flow

**Status:** ❌ Not Started
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

## Steps

- [ ] **1. Persist a "pending manual review" state** instead of a misleading
      `0.0`/`is_correct=False`. Add an answer-level grading status
      (e.g. `AUTO` | `PENDING_REVIEW` | `GRADED`) on the answer/score model; a
      `text` answer lands `PENDING_REVIEW`, excluded from the final score until
      graded. test-management-service schema is Alembic-owned → new
      `alembic revision --autogenerate`.
- [ ] **2. Session finalize semantics** — a session with ungraded `text` answers
      finalizes to a provisional score and a `needs_grading` flag; auto-only
      sessions are unaffected (regression-guard the existing scoring path).
- [ ] **3. Trainer grade endpoint** — `PATCH`/`POST` to set a `text` answer's
      score (0..1) + optional feedback, TRAINER-gated (reuse W4-F3 `require_trainer`
      pattern). Recompute the session score on grade. Add `ROUTES` entry only if a
      new URL pattern is introduced (existing `^/v1/api/...` may already cover it).
- [ ] **4. Trainer "to grade" queue** — list endpoint of sessions/answers awaiting
      review (filter by test), so trainers find ungraded work.
- [ ] **5. Frontend grader surface** — minimal trainer UI to view a pending `text`
      answer + its question/sample answer and submit a score+feedback. Reuse
      existing trainer dashboard auth/route conventions.
- [ ] **6. Tests** — scoring dispatch for `text` → PENDING (unit); finalize with a
      mix of auto + text answers (integration); grade endpoint RBAC 401/403/200 and
      score recompute; frontend grader render + submit.

## Out of scope

- Auto-grading `text` via NLP/LLM similarity — manual grading only here.
- Rubric/partial-rubric grading models beyond a single 0..1 score + feedback.

## Acceptance

- [ ] A `text` answer is recorded `PENDING_REVIEW`, never a silent `0.0`.
- [ ] A trainer can grade it; the session score recomputes; participant results
      (W4-F2) reflect the graded score.
- [ ] Tests above green; `FEATURE_STATUS.md` row flipped to ✅ with evidence.
