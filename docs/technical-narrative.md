# Technical narrative — two features

A one-page account of two features that carry the platform's core design
decisions, each tied to an ADR.

## 1. Quiz scoring engine (W3-F2)

**What.** When a candidate submits an answer, the platform scores it against the
question's correct-answer key and advances the session. Single-select questions
(MCQ, TRUE_FALSE) are graded all-or-nothing; multi-select (MULTI) questions earn
proportional partial credit; the session finalises on the last question.

**Why.** A scored exam needs a defensible grade for *partial* multi-select
answers — rewarding "3 of 4 correct" the same as a blank answer would be unfair
and would discard real signal. The metric also has to resist gaming ("select
everything"). The chosen answer is the **Jaccard index**
(`|correct ∩ submitted| / |correct ∪ submitted|`), which rewards partial
knowledge but shrinks the score for both missed and wrong picks. The reasoning
and the rejected alternatives (exact-match, recall) are in
[ADR 0002](adr/0002-multi-select-scoring-algorithm.md).

**How.** Scoring lives in `services/test-management-service/src/scoring/` as two
**pure** modules — `exact_match` (set equality → 0/1) and `partial_credit`
(Jaccard, delegating single-select to exact-match). Purity means the whole
type × outcome matrix is unit-tested without a database. The answer endpoint
(`session_service.submit_answer`) wraps scoring in a pessimistic row lock plus an
idempotency ledger (the `quiz_answers` table doubles as the dedup record), so a
retried or replayed submission scores exactly once. Unscorable TEXT raises
`ValueError`, which the endpoint catches as `manual_grading_required` so a bad
question type can't wedge a session.

## 2. Reporting & analytics service (W4-F1)

**What.** A separate service exposes candidate result reports — a per-user
summary (total attempts, average/best score, time spent, most-recent attempt)
and a paginated, filterable attempt history — at `/v1/api/reports/*`.

**Why.** Reports are read-heavy and analytically distinct from exam-taking, so
they belong in their own service. The hard question was how that service reaches
data owned and written by test-management (`sessions`, `quiz_answers`, `tests`).
The decision — **shared-DB direct read** with read-only models, over HTTP calls
or an event-projection mirror — trades a known schema coupling for zero sync
code and always-fresh reads, which is the right call at this scale. Full
reasoning and alternatives in
[ADR 0001](adr/0001-reporting-cross-service-data-access.md).

**How.** Reporting runs two engines: a read-only `tms_engine` mapping minimal
read-only models (`src/models/tms_readonly.py`) onto test-management's tables in
`eval_ai_dev`, and its own small `reporting-postgres` holding nothing but an
isolated `alembic_version` (two Alembic chains can't share one). Summaries are a
single round trip — `func.avg/count/sum` over a per-session-score subquery —
with SUBMITTED-only aggregates, percentage scores, and NULL scores until an
attempt is submitted. The attempts list is paginated with whitelisted sort
fields and `nullslast()` ordering so in-progress attempts don't float to the top.

## Where the ADRs land

Both features made a non-obvious architectural choice with cheaper-but-worse and
better-but-costlier alternatives. ADR 0001 (cross-service data access) and ADR
0002 (multi-select scoring) record those choices so the trade-offs are auditable
rather than buried in the diff. The honest weak points — no integration tests,
schema coupling, TEXT auto-scoring stub — are tracked in
[technical-debt.md](technical-debt.md).
