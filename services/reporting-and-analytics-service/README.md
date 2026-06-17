# Reporting & Analytics Service

Read-heavy reporting over the evaluation platform's quiz data. Port **8004**;
gateway-routed at `/v1/api/reports/*`.

## Data access (two engines)

- **TMS engine (read-only)** → test-management's `eval_ai_dev`. Report queries
  `SELECT` from `sessions`, `quiz_answers`, `tests` via read-only models
  (`src/models/tms_readonly.py`) on a dedicated `tms_engine` / `get_tms_db`.
  This service never writes there and never emits DDL for those tables.
- **Own engine** → `reporting-postgres` (`eval_ai_reporting`). A private
  datastore holding only this service's `alembic_version`, so its Alembic chain
  is isolated from test-management's chain in the shared DB. It owns no domain
  tables — `0001_baseline` is an empty no-op and stays head.

Rationale in [docs/adr/0001-reporting-cross-service-data-access.md](docs/adr/0001-reporting-cross-service-data-access.md).

## Endpoints (W4-F1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reports/user/{user_id}` | Candidate summary over SUBMITTED attempts: total attempts, avg/best score, total time spent, most recent attempt. |
| `GET` | `/reports/user/{user_id}/attempts` | Paginated attempt history. Query: `page`, `size` (≤100), `test_id`, `from`/`to` (filter the attempt **start** date), `status`, `sort=field:direction` (field ∈ {submitted_at, created_at, score}; default `submitted_at:desc`). |

Scores are **percentages** (per-answer `[0,1]` fractions averaged per session,
×100). An attempt's score is `null` until it is SUBMITTED. Summary aggregates
cover SUBMITTED sessions only.

Service-level authorization is intentionally absent: the API gateway's JWT check
is the platform boundary. The trainer-only `require_trainer` gate and
self-access enforcement land in W4-F3.

## Tests

```bash
cd services/reporting-and-analytics-service
docker run --rm -v "$PWD":/app -w /app python:3.11-slim bash -c \
  "pip install -q -r requirements-dev.txt; python -m pytest tests/ -q"
```
Hermetic — in-memory SQLite (the read-only TMS tables built on `TmsBase`), no
Postgres needed.
