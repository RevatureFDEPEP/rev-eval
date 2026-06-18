# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**rev-eval** — the Revature Evaluation Platform, a local-first microservices app run via Docker Compose. It is the brownfield substrate trainees extend during the FDE PEP program; several services/features are **intentionally incomplete** as candidate tasks (see Gotchas).

`docker-compose.yml` is the source of truth for what actually runs — trust it over `start.sh` / `test-services.sh`, which are stale and reference services (Consul, WorkOS, notification/AI services, lambda) that do not exist here.

## Stack & topology

| Service (compose name) | Port | Store | Notes |
|---|---|---|---|
| `api-gateway` | 8000 | — | JWT verify + regex pattern routing |
| `test-management-service` | 8001 | Postgres | tests, skills, submissions, dashboards |
| `user-service` | 8002 | Postgres | auth (issues JWT), users |
| `question-management-service` | 8003 | Mongo + MinIO | question bank, image uploads (Beanie ODM) |
| `reporting-and-analytics-service` | 8004 | Postgres | scaffolded (W2-M10); endpoints land in W4-F1 |
| `frontend` | 3000 | — | Next.js 16 / React 19 / TS, pnpm |
| `nginx` | 80 | — | **returns 502 by design** until wired (candidate task) |
| postgres / reporting-postgres / mongo / minio | 5432 / 5433 / 27017 / 9000 (console 9001) | | MinIO creds `minioadmin`/`minioadmin` |

`user-service` and `test-management-service` **share one Postgres DB** (`eval_ai_dev`).
`reporting-and-analytics-service` has its own **`reporting-postgres`** (`eval_ai_reporting`, host port 5433) — the spec's 2-Postgres topology.

### Auth / request flow (read before touching auth)

1. Login = POST to `user-service` (via gateway) → issues **HS256 JWT**, bcrypt-hashed passwords.
2. Frontend stores JWT in an **httpOnly cookie `auth_token`**.
3. Browser hits Next.js **BFF** routes under `frontend/src/app/api/`; the generic proxy `api/v1/[...path]/route.ts` lifts the JWT from the cookie (`getSession()`) and forwards it as a `Bearer` header to the gateway.
4. **`api-gateway` (`services/api-gateway-service/main.py`)** verifies the JWT, then does smart routing: the `ROUTES` regex table maps URL patterns → service (no service name in the URL). `/v1/api/auth/login` and `/register` are public pass-throughs. It injects `X-User-Id` / `X-User-Email` / `X-User-Role` headers downstream.
5. **Downstream services trust those `X-User-*` headers** and do not re-verify the JWT — the gateway is the only auth boundary. Bypassing it with spoofed headers would be trusted.
6. `frontend/src/middleware.ts` separately decodes the cookie JWT client-side for role-based route protection (`TRAINER`/`ADMIN` → `/trainer`, `PARTICIPANT` → `/participant`).

When adding a routable endpoint, you must add its URL pattern to `ROUTES` in the gateway `main.py` — services are not auto-discovered.

## Backend service layout (identical across all FastAPI services)

```
main.py                 # FastAPI app, CORS, router includes (prefix /v1/api), startup init_db()
src/v1/routes/          # HTTP endpoints (thin)
src/services/           # business logic
src/repositories/       # data access
src/models/             # SQLAlchemy models (async) OR Beanie Documents (question-service)
src/schemas/            # Pydantic request/response models
src/config/settings.py  # pydantic-settings, env-driven
src/db/session.py       # engine/session + init_db()
```

Postgres services use **async SQLAlchemy** (`asyncpg`); `question-management-service` uses **Beanie/Motor** over Mongo. **test-management-service's schema is owned by Alembic** (`alembic/versions/`, applied by its `start.sh`; its `init_db()` is connectivity-check only) — model changes there need an `alembic revision --autogenerate`. The other services still create tables on startup via `init_db()`/`create_all`.

## Frontend (`frontend/`)

Next.js App Router. `src/lib/api/` has two client layers: `client.ts` for browser→BFF calls and `server.ts` (`server-only`) for Server Components calling the gateway directly. UI is shadcn/Radix in `src/components/ui/`. Role dashboards under `src/app/(dashboard)/{trainer,participant}`.

## Commands (run from repo root unless noted)

```bash
# Full stack
cp .env.example .env          # defaults work for local dev; set JWT_SECRET for non-local
docker compose up --build
docker compose logs -f test-management-service

# Frontend (cd frontend) — pnpm only
pnpm install
pnpm dev                      # next dev --turbo on 0.0.0.0:3000
pnpm build
pnpm lint                     # eslint

# One backend service locally (cd services/<svc>)
pip install -r requirements.txt
python main.py                # or: uvicorn main:app --reload --port <port>
# test-management-service only: apply migrations first (also seeds demo data)
alembic upgrade head

# Migrations (cd services/test-management-service; compose runs this on startup)
alembic upgrade head          # demo tests/skills/categories seed in revision 0003
alembic revision --autogenerate -m "..."   # after model changes

# Seed demo data (all seeded users share password "password123")
# users: seeded by user-service on startup; tests/skills/categories: Alembic 0003
# question bank: auto-seeded by question-management-service on startup when the
#   bank is empty (idempotent, W5-F4); gated by SEED_QUESTION_BANK (default
#   true, compose-set). Set SEED_QUESTION_BANK=false for prod-like profiles.
#   The standalone HTTP script below remains for manual/remote seeding:
python services/question-management-service/seed_rag_context_questions.py
```

### Tests

- **Backend:** pytest, per-service. CI runs `pytest --cov` only when `services/<svc>/tests/` exists — **most services have no `tests/` yet** (adding them is a candidate task). Single test: `pytest tests/test_x.py::test_name` from the service dir.
- **Frontend:** `pnpm test` (no runner configured yet; CI uses `--if-present`).
- **CI** (`.github/workflows/ci-pipeline.yml`): matrix build+test for the 4 backend services + frontend lint/build/provenance, on push to `main` and all PRs. Trivy + Ruff gates are **not** seeded (candidate Day 7 task).

## Gotchas

- `nginx` returning **502 is the intended start state**, not a bug.
- `reporting-and-analytics-service` is scaffolded (W2-M10) on its own
  `reporting-postgres` under Alembic (empty `0001` baseline); business endpoints
  and the gateway `ROUTES` entry land in W4-F1.
- `start.sh` / `test-services.sh` are stale/aspirational — ignore their service lists.
- A checked-in `services/test-management-service/dev.db` (SQLite) exists from local experiments; deployed config uses Postgres.
- Compose service name is `api-gateway` (not `api-gateway-service`), though its dir is `services/api-gateway-service/`.
