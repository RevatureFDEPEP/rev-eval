# ADR W4-F1 — Reporting Service Data Access Pattern

**Date:** 2026-06-17
**Status:** Accepted
**Feature:** W4-F1 (Candidate Results Reporting Endpoints)

---

## Context

The reporting-and-analytics-service needs to serve aggregate quiz results
(`GET /reports/user/{id}` and `GET /reports/user/{id}/attempts`). The
source data — `quiz_sessions` and `session_answers` — lives in `eval_ai_dev`,
the test-management service's Postgres database. Three patterns were considered.

---

## Options Considered

### Option A: Direct-read (shared Postgres, second engine)
The reporting service opens a second SQLAlchemy engine pointing to `eval_ai_dev`
(same host/port/credentials as the primary reporting DB, different `DB_NAME`).
Read-only mirror models map to the `quiz_sessions` and `session_answers` tables.

**Pros**
- Real-time data; no sync lag.
- Enables the required `func.avg/count/sum` aggregate queries in a single round-trip.
- Minimal new code; no event infrastructure.

**Cons**
- Cross-service DB coupling: reporting must stay schema-aware of test-management tables.
- test-management schema changes may silently break reporting queries.
- Both services share Postgres credentials for `eval_ai_dev`.

### Option B: HTTP calls to test-management API
Reporting service calls `GET /sessions?user_id=X` on test-management for each request.

**Pros** — clean service boundary, no schema coupling.  
**Cons** — cannot do server-side aggregation; requires fetching all pages to compute avg/best/total; latency and N+1 risk; upstream rate-limited by test-management.

### Option C: Event projection / mirror table
test-management publishes a `session.submitted` event; reporting projects it into a
`reporting_dev.session_summaries` table. Queries run entirely against `reporting_dev`.

**Pros** — full service isolation; reporting can add its own indexes/denormalisations.  
**Cons** — requires an event bus (Kafka/RabbitMQ/pg_notify) not present in the stack; eventual consistency; additional operational complexity; premature for current scale.

---

## Decision

**Option A — Direct-read.** For the current phase of the project (single Postgres
instance, two databases on the same host), direct-read avoids event-infrastructure
overhead while still enabling the SQLAlchemy aggregate patterns required by the
curriculum spec. The coupling risk is accepted and mitigated by using read-only
mirror models with only the columns the reporting queries need.

The Alembic migration `0002_direct_read_adr.py` is a no-op: no tables are created
in `reporting_dev` as a result of this decision.

---

## Consequences

- `src/db/session.py` in reporting-and-analytics-service defines `eval_ai_engine`
  (connects to `eval_ai_dev`) alongside the primary `reporting_dev` engine.
- `src/models/quiz_session.py` and `src/models/session_answer.py` are read-only
  mirrors; they are **never** used for writes or migrations.
- If test-management renames or drops columns used by these queries, reporting
  will break at runtime. A schema-contract test should be added as follow-on work (W4-F5).
- Re-evaluate Option C if a message broker is introduced or if reporting queries
  need to join across services (e.g., user profile data).
