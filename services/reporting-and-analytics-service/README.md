# Reporting & Analytics Service

A FastAPI service on port **8004** that answers analytics questions about assessments: how a test performed, how its questions performed, who ranked where, and how an individual participant is doing.

## Endpoints

All under `/v1/api/reports`, reached through the API gateway.

| Endpoint | Returns |
|----------|---------|
| `GET /tests/{test_id}` | per-test analytics report |
| `GET /aggregate` | aggregate analytics across active tests |
| `GET /tests/{test_id}/questions` | per-question statistics for a test |
| `GET /tests/{test_id}/rankings` | ranked leaderboard for a test |
| `GET /user/{user_id}` | summary for a participant: attempts, average and best score, latest attempt |
| `GET /user/{user_id}/attempts` | paginated attempt history |

Trainer endpoints require the `TRAINER` role. A participant can read only their own summary and attempts. The service decodes the JWT itself as defence in depth, in addition to the gateway.

## Design

The service reads the PostgreSQL database that test-management-service writes, with read-only queries, instead of calling that service over HTTP or maintaining its own projection. The trade-offs are recorded in [ADR 0001](adr/0001-direct-db-read.md). Schema changes for reporting (indexes) are managed with Alembic (`alembic/versions/0001_reporting_indexes.py`).

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md).

```bash
cd services/reporting-and-analytics-service
pip install -r requirements.txt
pytest        # tests/test_reports.py, tests/test_auth_jwt.py; fails below 80 % coverage
```
