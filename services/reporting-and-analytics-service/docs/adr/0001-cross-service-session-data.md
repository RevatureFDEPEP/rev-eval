# ADR 0001 — Sourcing session/attempt data for the reporting service

- Status: Accepted
- Date: 2026-06-18
- Deciders: Reporting & Analytics team

## Context

The reporting-and-analytics-service needs to answer questions about a user's
quiz attempts: how many attempts they have made, their average/best score, how
much time they spent, and what their most recent attempt was.

The authoritative data lives in **test-management-service**, which owns the
`sessions` and `session_answers` tables (added in that service's migrations
`001` and `002`). A "session" is one attempt at a test.

The reporting endpoints are **read-heavy and latency-sensitive** — they run
`COUNT`, `AVG`, `SUM`, `MAX` aggregates and paginated, filtered, sorted scans
over a user's full attempt history. We have to decide how this service obtains
that data. Three patterns were considered.

### Option A — Synchronous API call to test-management-service

Reporting calls `test-management-service` over HTTP on every request.

- ✅ No data duplication; always reads the live source of truth.
- ❌ Aggregations (`AVG`/`SUM`/`COUNT` over potentially thousands of rows)
  cannot be pushed down to SQL — reporting would have to page the whole history
  over HTTP and aggregate in Python.
- ❌ Couples reporting availability and latency to test-management.
- ❌ Pagination/sorting/filtering would have to be re-implemented and forwarded.

### Option B — Direct cross-service database read

Reporting reads `test-management`'s tables directly from the shared Postgres
instance.

- ✅ Full SQL power, no duplication.
- ❌ Breaks service-ownership boundaries — reporting becomes coupled to another
  service's schema and migration cadence. A column rename in test-management
  silently breaks reporting.
- ❌ The shared database is a deployment convenience, not a contract; treating
  another service's tables as an API is an anti-pattern.

### Option C — Event projection into a local mirror table (chosen)

Reporting owns a denormalized `session_mirror` table in **its own** schema
namespace. test-management projects a compact event (one row per attempt /
attempt-state-change) into this mirror; reporting reads only its own table.

- ✅ Aggregates, pagination, filtering and sorting are plain local SQL —
  exactly what endpoints 2 and 3 need, with indexes the reporting team controls.
- ✅ Reporting stays available and fast even if test-management is down.
- ✅ Clear ownership boundary: the **event shape** is the contract, not another
  service's table layout.
- ⚠️ Eventual consistency (the mirror lags the source by the projection delay).
  Acceptable for analytics/reporting.
- ⚠️ Requires a projection mechanism and a denormalized copy.

## Decision

We adopt **Option C — event projection into a local `session_mirror` table.**

The mirror is denormalized specifically for reporting reads and holds exactly
the fields the report envelopes need: `user_id`, `test_id`, `status`, `score`,
`time_spent_seconds`, and timestamps. Its Alembic migration (`001`) lives in
this service.

The projection writer (the publisher in test-management and/or a consumer here)
is tracked as follow-up work. Until the event bus is wired up, the mirror is
populated by a backfill/projection job and is seeded directly in tests. The
read API in this service is written against the mirror only, so the read path
is unaffected by how rows arrive.

## Consequences

- The reporting read endpoints depend only on `session_mirror`; they never call
  test-management at request time.
- Reporting must tolerate eventual consistency and missing-not-yet-projected
  rows (a brand-new user simply has zero attempts).
- If/when an event bus is introduced, only the projection writer changes — the
  schema, repository, and endpoints stay the same.

## Notes on related decisions

### Schema source of truth: Alembic, not `create_all`

The Alembic migration (`alembic/versions/001_…`) is the authority for the
`session_mirror` schema. `start.sh` runs `alembic upgrade head` on boot (falling
back to `Base.metadata.create_all` only if that fails, so a fresh local/test DB
still comes up). `init_db()`’s `create_all` remains for the test fixtures, which
build the schema directly from the model. The model and the migration are kept
in lock-step; the migration — not `create_all` — is what runs in real
environments, so the two cannot silently drift in deployment.

### Database instance: shared Postgres for now

The spec sketches a dedicated `reporting-postgres`. This service currently
points at the **shared** Postgres instance (its own `session_mirror` table, in
its own logical space). That keeps the local stack to one database while the
mirror is still seeded/backfilled rather than fed by a live event stream.
Because the read path depends only on `session_mirror`, moving to a separate
reporting database later is a connection-string change plus running this
service’s migrations against the new instance — no code changes. The
ownership boundary (the event shape) is unaffected by where the table lives.
