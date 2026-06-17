# ADR 0001 — Reporting cross-service data access

- **Status**: Accepted
- **Date**: 2026-06-17
- **Feature**: W4-F1 (Candidate Results Reporting Endpoints)

## Context

`reporting-and-analytics-service` serves read-heavy candidate/trainer reports
(summaries, attempt history, aggregates). The source data — `sessions`,
`quiz_answers`, `tests` — is owned and written by `test-management-service`.
Reporting needs to read that data; it never writes it.

Three ways to get at it were considered:

1. **Shared-DB direct-read** — reporting connects to the same `eval_ai_dev`
   Postgres and maps read-only ORM models onto the existing tables.
2. **HTTP calls** — reporting fetches via new endpoints on test-management.
3. **Mirror table + projection** — reporting owns a copy, kept in sync by an
   event/projection pipeline.

## Decision

**Shared-DB direct-read, with an isolated bookkeeping datastore.** Reporting
defines read-only SQLAlchemy models (`src/models/tms_readonly.py`, on a separate
`TmsBase`) bound to test-management's `sessions`/`quiz_answers`/`tests` and
queries them over a dedicated read-only engine (`tms_engine` / `get_tms_db`,
pointed at `eval_ai_dev`). It never writes there and never emits DDL for those
tables.

Reporting owns no domain tables. It does, however, get its **own** small
Postgres (`reporting-postgres` / `eval_ai_reporting`) so its Alembic chain and
`alembic_version` are isolated from test-management's chain — two Alembic
histories cannot safely share one `alembic_version` row in the same database.
`0001_baseline` is therefore an empty no-op that stays head; it exists only to
make `alembic upgrade head` a valid bootstrap, satisfying the "working Alembic
environment" prerequisite without inventing tables this service doesn't own.

## Consequences

**Positive**
- Low effort: no changes to test-management, no sync/backfill code, no message
  bus. The only added infra is a small bookkeeping Postgres.
- Always-fresh reads (no projection lag / eventual consistency).
- Aggregates run server-side with `func.avg/count/sum` + a per-session-score
  subquery (summary is a single round trip), so the frontend never
  re-aggregates. Adequate at the platform's scale (hundreds of rows/candidate).
- The separate `tms_engine` + own `alembic_version` keep this service's
  migration lifecycle independent of test-management's, despite reading its data.

**Negative**
- **Schema coupling**: reporting's read-only models must track any column
  rename/removal in test-management. Mitigation: the models are a documented,
  minimal column subset on `TmsBase`, flagged read-only, and integration tests
  will catch drift (W3-F5/W4 test passes).
- Reads cross into test-management's database — no read-replica isolation.
  Acceptable now; revisit if reporting query load contends with live exam writes
  (at which point the mirror-table alternative below becomes attractive).

## Alternatives considered

- **HTTP calls** — clean service boundary and no schema coupling, but requires
  adding aggregation endpoints to test-management (out of F1 scope) and incurs
  per-aggregate network latency / N+1 risk. Rejected as premature for the scale.
- **Mirror table + projection** — best read isolation and scale headroom, but
  needs a sync/event path that does not exist (no message bus in the stack),
  plus backfill and eventual-consistency handling. ~2–3× the code for a
  performance benefit not observable at current scale. Rejected as overkill;
  reconsider if reporting outgrows the shared database.
