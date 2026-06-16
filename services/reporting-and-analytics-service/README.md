# Reporting & Analytics Service

Read-heavy service that serves candidate results and trainer dashboards
(reporting endpoints land in W4-F1; trainer aggregate/RBAC endpoints in W4-F3).

- **Port:** 8004
- **Database:** the shared `eval_ai_dev` PostgreSQL — **read-only**. This service
  reads `quiz_sessions` / `session_answers` (owned by `test-management-service`)
  and computes aggregates directly in SQL. It owns no tables of its own.

## Cross-service data access

The service reads test-management's data **directly from the shared database**
(shared-DB read-only), rather than over HTTP or via a mirror table. The decision,
trade-offs, and alternatives are recorded in
`docs/adr/0001-cross-service-data-access.md` (added in W4-F1).

## Authorization

This service does **not** decode JWTs. The API gateway verifies the JWT and
injects `X-User-Id` / `X-User-Email` / `X-User-Role`; trainer-only endpoints
(W4-F3) enforce the role by reading `X-User-Role`, matching the platform's
auth contract.

## Migrations

The service owns no tables, so `start.sh` runs **no** Alembic migrations —
running them would touch the `alembic_version` row that `test-management-service`
owns in the same database. The Alembic environment is scaffolded for future
reporting-owned tables and is configured with an isolated `version_table`
(`reporting_alembic_version`) so it can never collide with test-management's
migration history.

## Local development

```bash
pip install -r requirements.txt -r dev-requirements.txt
ruff check .
ruff format --check .
pytest
```

The full stack runs via Docker Compose from the repo root (`./start.sh`).
Health: `GET /health → {"status": "ok"}`.
