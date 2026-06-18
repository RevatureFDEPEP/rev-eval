# Verbal defence of AI-assisted code

This note backs the inline `AI-assisted (Claude Code)` comments. For each
section: **what the AI produced**, **what we changed**, **why the final shape
was chosen**. The point is that AI drafted boilerplate-shaped logic and a human
owned every correctness and policy decision.

## 1. Scoring engine — `exact_match.py` / `partial_credit.py`

**What the AI produced.** Two pure scorer functions sharing a `_normalise`
helper (case-fold + strip into a `frozenset`), returning a common `ScoreResult`
dataclass. The AI drafted the Jaccard formula (`|A∩B| / |A∪B|`), the full-match
set-equality branch, and the single-answer comparison.

**What we changed.** (a) Pointed Jaccard at **free-text only** and made
multi-select use full-match — the AI's first pass applied partial credit more
broadly; we narrowed it because partial credit blurs the pass/fail signal a
knowledge check needs (documented in ADR 0002). (b) Made the unrecognized-type
path an explicit, intentional fallback to single-answer exact match so a
malformed `type` field degrades safely instead of raising. (c) Added the
both-sets-empty → full-credit edge case deliberately.

**Why this shape.** Pure functions with no DB/IO are trivially unit-testable and
reusable; the caller selects a scorer by type and stays agnostic. The strict
multi-select rule keeps `is_correct` a clean boolean that the reporting
aggregates depend on.

## 2. Scorer selection — `session_service.py` step 5

**What the AI produced.** An inline conditional choosing `partial_credit` vs
`exact_match` based on question type.

**What we changed.** Lifted the type list into a single module-level
`_PARTIAL_CREDIT_TYPES` set so the routing policy lives in exactly one place,
and confirmed multi-select falls through to `exact_match`.

**Why this shape.** Centralizing the policy makes "move multi-select to partial
credit" a one-line change and keeps ADR 0002 honest — there is one source of
truth for which types get partial credit.

## 3. Reporting aggregate query — `report_repository.get_user_summary`

**What the AI produced.** A single `select` combining `count`/`avg`/`sum`/`max`
with a scalar subquery for the most-recent attempt id.

**What we changed.** Chose to resolve the most-recent row via an id subquery
rather than a second full scan; added a deterministic `(created_at desc,
session_id desc)` tiebreak so "most recent" is stable when timestamps collide;
and coerced NULL aggregates to `0`/`0.0` so a brand-new user returns zeros, not
nulls.

**Why this shape.** One round-trip instead of several; the local-SQL aggregation
is the entire justification for ADR 0001's mirror table — if we were calling
test-management over HTTP we could not push these aggregates down to the DB.
</content>
