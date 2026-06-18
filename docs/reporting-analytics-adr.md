# ADR: Reporting and Analytics Service — Data Access Strategy

## Status

Accepted

## Context

The reporting-and-analytics-service must answer per-user session performance queries against the `sessions` and `session_answers` tables, which are owned and written exclusively by test-management-service. There is no event bus in the current stack (no SQS, Kafka, or Redis Streams per CLAUDE.md). The service exposes two read-only GET endpoints:

- `GET /v1/api/reports/user/{user_id}` — aggregate summary envelope
- `GET /v1/api/reports/user/{user_id}/attempts` — paginated attempt history

`user_id` is an Integer throughout, consistent with the `users.id` Primary Key in user-service and the `sessions.user_id` column in test-management-service.

## Decision

The reporting-and-analytics-service connects read-only to the shared PostgreSQL instance (`eval_ai_dev`) — the same database container used by user-service and test-management-service. It declares SQLAlchemy ORM models that map to the existing `sessions` and `session_answers` tables without creating or migrating them. Alembic is configured as a baseline-only setup for forward extensibility.

The `sessions.status` column uses a Postgres enum type named `sessionstatus` that is owned by test-management-service. The reporting service redeclares it with `create_type=False` to prevent attempting a duplicate `CREATE TYPE` on startup.

## Alternatives Considered

### 1. Separate PostgreSQL database with a mirror table and polling (not selected)

A dedicated `reporting_sessions` table in a separate DB with an APScheduler background job to sync rows from the source database.

**Rejected because:**
- Requires watermark management (`last_synced_at`) and `INSERT ... ON CONFLICT DO UPDATE` logic
- Adds sync lag (typically 30–60 s for a polling interval)
- Adds a distinct failure mode: the reporting service diverges silently when the sync job fails
- No meaningful isolation benefit — both databases run on the same host in the current stack
- Significant operational complexity for a v1 feature with no corresponding benefit

### 2. Event sourcing via SQS or a message broker (not selected)

test-management-service publishes session events to a queue; the reporting service consumes them and maintains its own read model.

**Rejected because:**
- Requires infrastructure changes: adding SQS, Kafka, or Redis to docker-compose
- Introduces eventual consistency — queries may lag behind writes by seconds to minutes
- Out of scope for the current stack as documented in CLAUDE.md

### 3. Shared DB, read-only connection (selected)

The reporting service opens a read-only connection to the same `eval_ai_dev` Postgres database. It issues only `SELECT` queries and never calls `Base.metadata.create_all` for the mapped tables.

**Accepted because:**
- Zero sync complexity and perfect read consistency (reads live data)
- Compatible with the existing single-postgres docker-compose setup (no infra changes)
- Service is stateless with respect to DB writes — it cannot corrupt source data
- Simpler to reason about and test

**Trade-off:** The reporting service is tightly coupled to test-management-service's table schema. Any rename or removal of columns in `sessions` or `session_answers` must include a corresponding update to the reporting service's models.

## Consequences

- Reporting service has a read-only dependency on test-management-service's table schema. Schema changes to `sessions`/`session_answers` must account for active reporting queries.
- The Alembic baseline migration (`a1b2c3d4`) provides a starting point to promote to a full schema with a polling sync job if isolation becomes necessary in the future (e.g., multi-tenant deployment, separate Postgres instance per environment).
- The reporting service runs on port **8004** and is added to docker-compose with `depends_on: test-management-service: service_healthy` to guarantee tables exist before the first connection.
