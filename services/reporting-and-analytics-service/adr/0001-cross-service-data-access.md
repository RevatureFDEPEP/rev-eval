# 0001. Reporting service reads test-management data via shared-DB direct read

- Status: Accepted
- Date: 2026-06-16
- Deciders: rev-eval team
- Context features: W4-F1 (Candidate Results Reporting Endpoints)

## Context

The reporting-and-analytics-service must serve read-heavy candidate results
(summary envelopes, attempt history, and — in W4-F3 — cross-test aggregates).
Its source data is the `quiz_sessions` and `session_answers` tables, which are
written and owned by test-management-service.

Relevant facts about the current topology:
- There is a single shared PostgreSQL instance (`eval_ai_dev`); user-service and
  test-management-service already both connect to it.
- The reports are aggregate-shaped: per-session score is `SUM(points_earned) /
  SUM(max_points)`, and W4-F3 needs GROUP BY / window-function queries (pass rate,
  RANK(), percentile_cont) across the full sessions/answers dataset.
- This is a local-first evaluation platform run via Docker Compose, not a
  horizontally-scaled production system.

We must decide how the reporting service obtains this data.

## Decision

The reporting service connects to the **same `eval_ai_dev` Postgres database**
and reads `quiz_sessions` / `session_answers` directly through **read-only ORM
models**. It owns no copy of this data, defines no mutating operations on these
tables, and creates no Alembic migration for them (its Alembic environment is
scaffolded with an isolated `version_table` and is ready for any
reporting-owned tables added later).

## Consequences

Positive:
- Aggregate queries (GROUP BY, HAVING, window functions) run natively in SQL in a
  single round trip — no client-side re-aggregation, no N+1 fan-out.
- No synchronization machinery, no data duplication, no eventual-consistency window.
- Lowest implementation and operational cost; fits the single-Compose-stack model.

Negative / accepted trade-offs:
- Reporting is coupled to test-management's schema: a column rename or table change
  in test-management can break reporting. Mitigated by (a) read-only models so
  reporting can never corrupt source data, (b) keeping the mapped surface minimal,
  and (c) a cross-schema `--integration` test that seeds through test-management's
  own Alembic-migrated tables and asserts reporting's queries still resolve, so
  schema drift fails CI rather than production.
- The two services share a database, weakening the "database-per-service" boundary.
  Accepted deliberately for a local-first platform; if reporting later needs its own
  datastore or independent scaling, the migration path is the mirror-table /
  projection option below (this ADR would then be superseded).

## Alternatives considered

1. **HTTP calls to test-management-service.** Reporting calls new endpoints over
   httpx. Preserves the service boundary, but aggregate/GROUP BY queries would
   require either new bespoke aggregate endpoints in test-management or N+1 fan-out
   from reporting. More code, more latency, and it pushes reporting concerns into
   test-management. Rejected.

2. **Mirror table + event projection.** Reporting owns its own sessions/answers
   tables, kept in sync via events or a sync job. Most decoupled and the most
   scalable, but by far the most code (sync mechanism, migration, consistency and
   backfill handling) — unjustified for the current scale. Rejected, but retained as
   the documented evolution path.

## Notes on score semantics (W4-F1)

Derived from `session_answers` because there is no stored per-session score column:
- An **attempt** is any `quiz_sessions` row for the user; `total_attempts` counts all of them.
- **Per-session score** = `SUM(points_earned) / SUM(max_points)` over that session's
  answers (a 0..1 fraction); `None` when the session has no answers.
- **average_score / best_score** are over **SUBMITTED** sessions only. ACTIVE
  (in-progress) and EXPIRED (timed-out) sessions are attempts but are excluded from
  score stats so an abandoned attempt cannot drag a candidate's average down.
- **total_time_spent** = sum of `submitted_at − started_at` over SUBMITTED sessions,
  computed in Python (no portable cross-dialect interval SQL).
- **most_recent_attempt** = the attempt with the latest `created_at` (any status).
- The score formula lives in one place (`_raw_score`); the summary averages the raw
  fractions and rounds once, so it stays consistent with the per-attempt scores.
- Attempt-history **date filters apply to `created_at`** (always present) and are
  interpreted in **UTC**, matching test-management's tz-naive UTC timestamps.

## Verification

The schema-coupling risk this ADR accepts is guarded by the cross-schema
`--integration` suite (`tests/integration/test_reporting_real_pg.py`), which runs
reporting's real queries against a Postgres whose schema test-management migrated
(`docker compose up -d --wait postgres test-management-service`). It seeds rows
with raw SQL straight into test-management's own migrated tables — never via
reporting's `tms_readonly` mirror — so a renamed/dropped column or a changed enum
surfaces as a failed query, not a green test against a mirror that drifted.

This guard was confirmed to have teeth: renaming a mirror column
(`points_earned` → a non-existent name) left the **hermetic** suite green (it
builds its schema from the mirror, so the mirror agreed with itself) while the
**integration** suite failed with `column "…" does not exist` on real Postgres —
the exact drift the suite exists to catch. Reverted; both suites green.

Coverage as of W4-F1: 26 hermetic + 5 cross-schema integration tests; the
integration step runs in CI gated on the reporting matrix entry. The endpoints
were additionally live-smoked against the running stack — summary figures, the
native-enum `status` filter, and the `require_self_or_trainer` gate (participant
self → 200, cross-user → 403, trainer → 200) through the gateway.
