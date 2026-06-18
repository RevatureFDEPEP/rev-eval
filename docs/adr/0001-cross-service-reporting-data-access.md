# ADR 0001 — Cross-service data access for the reporting service

- **Status:** Accepted
- **Date:** 2026-06-18
- **Deciders:** Reporting & Analytics team
- **Scope:** Project-level. A service-local copy lives at
  [reporting-and-analytics-service/docs/adr/0001](../../services/reporting-and-analytics-service/docs/adr/0001-cross-service-session-data.md);
  this is the canonical project record.

## Context

The reporting-and-analytics-service answers questions about a participant's quiz
attempts: total attempts, average/best score, total time spent, the most recent
attempt, and a paginated/filtered/sorted history. The authoritative data —
`sessions` and `session_answers` — is **owned by test-management-service**
(migrations `001`/`002`). A "session" is one attempt at a test.

The reporting reads are **read-heavy and latency-sensitive**: they run `COUNT`,
`AVG`, `SUM`, `MAX` aggregates and scan a participant's whole attempt history
with paging and filters. We had to decide how reporting obtains data owned by
another service. In a microservice system there are three standard patterns, and
the choice has long-lived coupling consequences, so it warrants an ADR.

## Decision

**Adopt event projection into a local, denormalized `session_mirror` table that
reporting owns (Option C below).**

test-management projects a compact per-attempt event into `session_mirror`;
reporting reads **only its own table**. The mirror holds exactly the fields the
report envelopes need — `user_id`, `test_id`, `status`, `score`,
`time_spent_seconds`, and timestamps — and ships with its own Alembic migration
([`001_add_session_mirror_table.py`](../../services/reporting-and-analytics-service/alembic/versions/001_add_session_mirror_table.py)).
All aggregation, pagination, filtering, and sorting are then plain local SQL over
indexes the reporting team controls (see
[report_repository.py](../../services/reporting-and-analytics-service/src/repositories/report_repository.py)).

The **event shape is the contract** between the two services — not another
service's physical table layout.

## Alternatives considered

### Option A — Synchronous API call to test-management-service
Reporting calls test-management over HTTP on every request.

- ✅ No duplication; always reads the live source of truth.
- ❌ `AVG`/`SUM`/`COUNT` over thousands of rows can't be pushed down to SQL —
  reporting would page the full history over HTTP and aggregate in Python.
- ❌ Couples reporting's availability and latency to test-management.
- ❌ Pagination/sorting/filtering would have to be re-implemented and forwarded.

### Option B — Direct cross-service database read
Reporting reads test-management's tables directly from the shared Postgres.

- ✅ Full SQL power, no duplication.
- ❌ Breaks service-ownership boundaries: a column rename in test-management
  silently breaks reporting.
- ❌ Treats the shared DB (a deployment convenience) as an API contract — an
  anti-pattern that defeats the point of separate services.

### Option C — Event projection into a local mirror (**chosen**)
- ✅ Aggregates/paging/filtering/sorting are local SQL with reporting-owned
  indexes — exactly what the endpoints need.
- ✅ Reporting stays fast and available even if test-management is down.
- ✅ Clear ownership boundary; the event shape is the contract.
- ⚠️ Eventual consistency — the mirror lags the source by the projection delay.
  Acceptable for analytics.
- ⚠️ Requires a projection mechanism and a denormalized copy.

## Consequences

- Reporting read endpoints depend only on `session_mirror`; they never call
  test-management at request time.
- Reporting must tolerate eventual consistency and not-yet-projected rows — a
  brand-new participant simply has zero attempts.
- **Follow-up (open):** the projection writer (publisher in test-management
  and/or a consumer here) is not built yet. Until an event bus is wired up, the
  mirror is populated by a backfill/projection job and seeded directly in tests.
  Because the read API is written against the mirror only, when the event bus
  lands **only the projection writer changes** — schema, repository, and
  endpoints stay the same. This gap is tracked in
  [technical-debt.md](../technical-debt.md) items 6.2.
</content>
