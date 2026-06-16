# ADR 0001 — Reporting data access: direct DB read vs. HTTP API vs. event projection

**Status:** Accepted  
**Date:** 2026-06-15

## Context

The reporting service needs quiz session scores, test metadata, and submission records to answer:
- Per-test aggregate stats (avg score, pass rate, distribution)
- Candidate result history (`/reports/user/{id}`)
- Ranked leaderboards

Three approaches were evaluated:

| Option | Description |
|--------|-------------|
| **A — Direct DB read** | Reporting service connects to the same Postgres instance as test-management-service and issues read-only queries |
| **B — HTTP API** | Reporting service calls `GET /v1/api/test-sessions?user_id=...` on test-management-service and aggregates in Python |
| **C — Event projection** | test-management-service publishes events (e.g. `session.completed`) to a queue; reporting service builds its own materialized view |

## Decision

**Option A — direct DB read**, sharing the `eval_ai_dev` Postgres database.

## Rationale

**Why not B (HTTP API):**
Aggregating across all sessions for a test requires fetching potentially thousands of records over HTTP. test-management-service has no bulk-export endpoint; building one would add scope to a service that should remain focused on session lifecycle. Pagination loops introduce latency and coupling: a reporting query now blocks on test-management availability.

**Why not C (event projection):**
Event-driven projection is the right long-term architecture for a true analytics store (ClickHouse, BigQuery). At this stage it requires a message broker, schema registry, and consumer — three new infrastructure components for a system that does not yet need horizontal read scale. Premature for W4.

**Why A:**
- No round-trip latency or N+1 HTTP calls
- Aggregate SQL (`GROUP BY`, `func.rank().over(...)`) runs in the database engine where it is most efficient
- Read-only queries do not compete with write-path transactions in any meaningful way at this load level
- The reporting service uses a separate SQLAlchemy `Base` and does not own any tables — it cannot accidentally mutate data

## Consequences

- Reporting service **must point at the same Postgres instance** as test-management-service (`DB_NAME=eval_ai_dev`). The platform's scaffolded `reporting-postgres` (`eval_ai_reporting`) does **not** hold `quiz_sessions` — do not use it for this service.
- If test-management-service migrates to a separate DB cluster in future, reporting queries must be moved to either Option B or Option C at that point.
- Alembic migrations for reporting indexes use a separate `alembic_version_reporting` table to avoid conflict with test-management-service's migration history.
