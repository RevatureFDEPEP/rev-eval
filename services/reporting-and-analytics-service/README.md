# Reporting and Analytics Service

Aggregates evaluation results into reporting/analytics views. Scaffolded on the
standard rev-eval FastAPI layout (W2-M10); candidate-results endpoints land in
**W4-F1**.

- **Port:** 8004
- **Store:** dedicated `reporting-postgres` instance (DB `eval_ai_reporting`),
  schema under **Alembic** (`alembic/versions/`).
- **Startup:** `start.sh` waits for Postgres, runs `alembic upgrade head`, then
  launches the app.

## Layout

```
main.py                 # FastAPI app, CORS, /v1/api router prefix, startup init_db()
src/v1/routes/          # HTTP endpoints (empty — W4-F1)
src/services/           # business logic (empty — W4-F1)
src/repositories/       # data access (empty — W4-F1)
src/models/             # SQLAlchemy models (empty — W4-F1)
src/schemas/            # Pydantic models (empty — W4-F1)
src/config/settings.py  # pydantic-settings (DB_*, env-driven)
src/db/session.py       # async engine/session + connectivity-check init_db()
alembic/                # migration env + versions (0001 = empty baseline)
```

## Local dev

```bash
pip install -r requirements-dev.txt
alembic upgrade head          # against a running reporting-postgres
python main.py                # or: uvicorn main:app --reload --port 8004
pytest --cov                  # hermetic; no DB needed
```

When adding routable endpoints, register their URL pattern in the api-gateway
`ROUTES` table — services are not auto-discovered.
