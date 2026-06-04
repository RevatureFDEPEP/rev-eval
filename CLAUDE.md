# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Rev-Eval is a local-first microservices training evaluation platform for Revature. Trainers author tests and assign them to participants; participants take tests; submissions are tracked. No external AI dependencies.

## Running the Full Stack

```bash
cp .env.example .env          # first time only
docker compose up --build     # build and start all services
docker compose up             # subsequent runs
```

Services start on: frontend `:3000`, api-gateway `:8000`, test-management `:8001`, user-service `:8002`, question-management `:8003`, MinIO console `:9001`.

## Frontend (Next.js + pnpm)

```bash
cd frontend
pnpm install
pnpm dev          # dev server on :3000 (Turbopack)
pnpm build        # production build
pnpm lint         # ESLint
```

Path alias `@/*` maps to `src/*`. TypeScript strict mode is on.

## Backend Services (Python 3.11 / FastAPI)

Each service in `services/<name>/` follows the same pattern:

```bash
cd services/<service-name>
pip install -r requirements.txt
python main.py               # uvicorn dev server
```

**Running tests:**
```bash
pytest tests/ -v                                    # all tests
pytest tests/test_foo.py::TestClass::test_method -v # single test
pytest --cov --cov-report=xml                       # with coverage
```

**Seeding test data** (test-management-service):
```bash
python seed_db.py   # default password: password123
```

Swagger UI is auto-generated at `/<service>/docs` when running.

## Architecture

```
frontend/                        Next.js App Router (role-based auth via middleware)
services/
  api-gateway-service/           JWT verification + routing (port 8000)
  user-service/                  Auth, JWT issuance, user CRUD (port 8002)
  test-management-service/       Tests, skills, submissions (port 8001)
  question-management-service/   Question bank, MinIO uploads (port 8003)
nginx/                           Reverse proxy config
docker-compose.yml               Full stack orchestration
```

### Auth Flow

1. Frontend POSTs credentials → user-service via gateway
2. user-service issues HS256 JWT (60 min, bcrypt passwords)
3. JWT stored as `auth_token` httpOnly cookie
4. `frontend/src/middleware.ts` decodes JWT on every request — enforces role routing
5. API Gateway re-validates JWT, injects `X-User-Id`, `X-User-Email`, `X-User-Role` headers for downstream services

### Backend Service Layout (consistent across services)

```
config/settings.py     Pydantic env loading
db/session.py          DB connection + table init
models/                SQLAlchemy (Postgres) or Beanie (MongoDB) ORM
schemas/               Pydantic request/response DTOs
repositories/          Data access (CRUD)
services/              Business logic
v1/routes/             FastAPI router endpoints
```

### Databases

| Store      | Used by                        | Notes                          |
|------------|--------------------------------|--------------------------------|
| PostgreSQL | user-service, test-management  | SQLAlchemy, tables auto-created |
| MongoDB    | question-management            | Beanie ODM, Motor async driver  |
| MinIO      | question-management            | S3-compatible, question images  |

### Frontend Route Structure

| Path            | Role         |
|-----------------|--------------|
| `/`             | Login        |
| `/dashboard`    | Role redirect |
| `/trainer/*`    | Trainer only |
| `/participant/*`| Participant only |


## Environment Variables

Copy `.env.example` to `.env`. Key variables: `JWT_SIGNING_SECRET`, Postgres credentials, MongoDB credentials, MinIO access keys, optional AWS SQS config.

## CI

`.github/workflows/ci-pipeline.yml` runs on PR/push:
- **Backend**: matrix over 4 services — pip install, pytest (skipped if no `tests/` dir)
- **Frontend**: pnpm install (frozen lockfile), lint, build, test if present
- Requires `JWT_SIGNING_SECRET` secret in GitHub
