# Reporting and Analytics Service

Read-only reporting over user quiz attempts. Exposes aggregate summaries and a
paginated attempt history for each user.

## Data source

This service does **not** call test-management-service at request time. It reads
a local, denormalized `session_mirror` table that is populated by an event
projection from test-management-service. The rationale (API call vs. direct DB
read vs. event projection) is documented in
[docs/adr/0001-cross-service-session-data.md](docs/adr/0001-cross-service-session-data.md).

## Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/reports/user/{user_id}` | Summary envelope: total attempts, average score, best score, total time spent, most recent attempt. |
| `GET` | `/reports/user/{user_id}/attempts` | Paginated, filtered, sorted attempt history. |
| `GET` | `/health` | Liveness probe. |

### `GET /reports/user/{user_id}/attempts` query parameters

| Param | Type | Default | Notes |
| ----- | ---- | ------- | ----- |
| `page` | int | `1` | 1-based page number (`>= 1`). |
| `size` | int | `20` | Items per page (`1..100`). |
| `test_id` | str | – | Filter by test identifier. |
| `from` | date | – | Attempts created on/after this date. |
| `to` | date | – | Attempts created on/before this date (inclusive). |
| `status` | enum | – | `ACTIVE`, `EXPIRED`, `COMPLETED`, `ABANDONED`, `SUBMITTED`. |
| `sort` | str | `created_at:desc` | `field:direction`, e.g. `score:desc`. Sortable fields: `created_at`, `submitted_at`, `started_at`, `score`, `time_spent_seconds`. |

## Local development

```bash
pip install -r requirements.txt
pip install -r ../requirements-dev.txt

# run migrations against Postgres
DATABASE_URL=postgresql+asyncpg://root:root@localhost:5432/eval_ai_dev alembic upgrade head

# run the service
python main.py            # serves on :8004
```

## Tests

```bash
pytest                    # uses in-memory SQLite (see conftest.py)
ruff check .
```

CORS is configured (Day 16) to allow the frontend origin `http://localhost:3000`
via `ALLOW_ORIGINS`.
