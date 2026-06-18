# ADR-0001: Cross-service data access for the reporting service

- **Status:** Accepted — implementation pending
- **Date:** 2026-06-18
- **Feature:** W4-F1 (Candidate Results Reporting Endpoints)
- **Code:** `services/reporting-and-analytics-service/` (scaffold)

## Context

The reporting-and-analytics-service must serve read-heavy candidate and trainer
reports — per-user summaries (`GET /reports/user/{id}`), paginated attempt
history, and trainer aggregates (pass rates, score distributions, per-question
difficulty). The data it reports on — quiz sessions and scored answers — is
owned and written by **test-management-service**, in its Postgres database
(`quiz_sessions`, `answers`, `test_submissions`). The reporting service has its
own service boundary and its own Alembic environment.

The reporting endpoints lean hard on relational aggregation: `GROUP BY`,
`func.avg`/`func.count`/`func.sum`, subqueries for "most recent attempt", and
window functions (`percentile_cont`, `RANK()`). The question is **how reporting
reads the source data** without forcing the frontend to re-aggregate.

At decision time the reporting service is scaffold-only (README), so this ADR
records the chosen direction for the implementation rather than describing
shipped code.

Three patterns were considered: direct shared-DB read, synchronous HTTP API
calls to test-management, and an event-projection / read-model mirror.

## Decision

Adopt a **sessions mirror (read-model) table** inside the reporting service,
populated from test-management's session/answer data, and run all aggregate
queries against that local mirror.

Rationale:

- Aggregates (`GROUP BY`, window functions, subqueries) are natural and fast
  against a **local relational table** the service owns and can index for its
  own access patterns. The reporting service keeps its own Alembic migrations
  for the mirror schema.
- It preserves the **service boundary**: reporting does not reach into another
  service's private schema, so test-management can evolve its internal tables
  without silently breaking reporting (the coupling becomes an explicit,
  versioned projection rather than a hidden shared schema).
- It matches the read-heavy, eventually-consistent nature of reporting —
  candidates and trainers do not need millisecond-fresh aggregates.

## Consequences

- **A projection/sync mechanism is now required** — the mirror must be populated
  (batch sync, on-submit write, or a later event stream). Until that exists the
  reporting endpoints have no data; this is tracked in `docs/technical-debt.md`.
- **Eventual consistency:** reports can lag the source by the sync interval.
  Acceptable for this domain; must be stated in the API docs so the frontend
  does not present stale aggregates as live.
- **Schema duplication:** the mirror restates a subset of `quiz_sessions` /
  `answers`. That is the deliberate cost of decoupling; the alternative (shared
  DB) trades this duplication for tight schema coupling.
- **CORS** for the frontend origin (`http://localhost:3000`) is configured on the
  reporting service independently (Day-16 requirement).

## Alternatives considered

- **Direct shared-DB read** — reporting opens a read-only connection to
  test-management's Postgres and queries `quiz_sessions`/`answers` directly.
  *Pros:* zero duplication, always fresh, aggregates run on the canonical tables.
  *Cons:* hard coupling to another service's private schema — a migration in
  test-management can break reporting with no compile-time signal; violates the
  service boundary. Strong, simplest MVP option; rejected for the coupling risk,
  but it is the natural fallback if the mirror's sync cost proves not worth it at
  cohort scale.
- **Synchronous HTTP API calls** — reporting calls test-management endpoints and
  aggregates in Python. *Pros:* clean boundary, no duplication. *Cons:*
  aggregation over HTTP is an N+1 / large-payload problem (you cannot `GROUP BY`
  across services in SQL), and it couples report latency to another service's
  uptime. Rejected for aggregate workloads; still the right call for one-off
  point lookups.
- **Full event projection (event log + async consumers)** — the textbook
  decoupled answer. Rejected as **over-engineered for cohort scale**: it adds a
  broker and consumer plumbing for a volume a periodic sync handles fine. The
  chosen mirror is a pragmatic middle point that can grow into this later.
