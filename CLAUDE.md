# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack overview

**rev-eval** is a local-first evaluation platform composed of:

- 4 Python 3.11 FastAPI microservices under `services/`
- 1 Next.js 16 (React 19, TypeScript) frontend under `frontend/`
- PostgreSQL 15, MongoDB 7, MinIO (S3-compatible), Nginx reverse proxy
- All wired together via Docker Compose

## Running the full stack

```bash
cp .env.example .env       # set JWT_SECRET and other secrets if needed
docker compose up --build  # starts all services + databases
```

Default dev passwords are `password123` for all seeded users (see `services/test-management-service/seed_db.py`).

Useful endpoints once running:

| URL | What |
|-----|------|
| http://localhost:3000 | Frontend |
| http://localhost:8000 | API Gateway |
| http://localhost:8001/docs | test-management-service Swagger |
| http://localhost:8002/docs | user-service Swagger |
| http://localhost:8003/docs | question-management-service Swagger |
| http://localhost:9001 | MinIO console (`minioadmin` / `minioadmin`) |

## Frontend commands

All run from `frontend/`:

```bash
pnpm install           # install dependencies
pnpm dev               # dev server (Turbopack) at localhost:3000
pnpm build             # production build
pnpm lint              # ESLint
pnpm test --if-present # run tests if they exist
```

Package manager is **pnpm** (v9). Never use npm or yarn here.

## Backend commands (per service)

Each service lives under `services/<service-name>/`. Install from the `src/` subdirectory:

```bash
cd services/<service-name>/src
pip install -r requirements.txt
pip install pytest pytest-cov
```

Run tests (from the service root):

```bash
cd services/<service-name>
pytest                          # all tests
pytest tests/test_foo.py        # single file
pytest tests/test_foo.py::test_bar  # single test
pytest --cov --cov-report=xml   # with coverage
```

Run a service locally (from service root, requires env vars):

```bash
python main.py
```

## Architecture: request flow

```
Browser
  → Next.js frontend (port 3000)
      → /api/auth/* routes → user-service directly (login/register only)
      → /api/v1/* catch-all BFF → API Gateway (port 8000) with Bearer token
          → API Gateway verifies HS256 JWT, injects X-User-Id/Email/Role headers
          → routes to downstream service by URL pattern
```

### Key wiring points

**Auth token**: user-service issues an HS256 JWT with claims `sub` (user id), `email`, `role`. The frontend stores it in an httpOnly cookie named `auth_token`. Next.js middleware (`frontend/src/middleware.ts`) decodes it (no crypto verify — backend is source of truth) for route guarding. The BFF catch-all (`frontend/src/app/api/v1/[...path]/route.ts`) reads `getSession()` and injects `Authorization: Bearer <token>` on every call to the gateway.

**Gateway routing** (`services/api-gateway-service/main.py`): regex patterns match the URL path to a service. `/v1/api/auth/*` is a public pass-through with no JWT check. All other paths require a valid JWT; the gateway adds `X-User-*` headers before forwarding.

**Downstream auth**: services like test-management-service never see the JWT directly. They extract identity from `X-User-Id`, `X-User-Email`, `X-User-Role` headers (see `services/test-management-service/src/utils/dependencies.py`). When they need full user data they call user-service by HTTP.

**Gateway route table** (in `main.py`):
- `/v1/api/auth/**` → user-service:8002 (public)
- `/v1/api/users/**` → user-service:8002
- `/v1/api/tests/**`, `/v1/api/submissions/**`, `/v1/api/skills/**`, `/v1/api/dashboard/**` → test-management-service:8001
- `/v1/api/questions/**` → question-management-service:8003

## Service internal structure

Each service follows the same layered layout:

```
services/<name>/
  main.py               # FastAPI app wiring, CORS, router registration, startup
  requirements.txt      # Python deps (install from src/ dir in CI)
  src/
    config/settings.py  # pydantic-settings env config
    db/session.py       # DB engine + session factory + init_db()
    models/             # SQLAlchemy ORM models (Postgres services) or Beanie Documents (Mongo)
    schemas/            # Pydantic request/response schemas
    repositories/       # DB queries (data access layer)
    services/           # Business logic
    v1/routes/          # FastAPI routers mounted at /v1/api
    utils/dependencies.py  # FastAPI Depends() helpers (auth extraction)
```

**user-service** and **test-management-service** use SQLAlchemy async (asyncpg) on PostgreSQL. **question-management-service** uses Beanie ODM on MongoDB.

## Data models

- **User** (`user-service`): `TRAINER` or `PARTICIPANT` role. Stored in Postgres `users` table.
- **Question** (`question-management-service`): Beanie Document in MongoDB `questions` collection. Types: `mcq`, `multi`, `true_false`, `text`.
- **Test**, **Skill**, **TestSkill**, **TestSubmission** (`test-management-service`): Postgres tables via SQLAlchemy async.

## Frontend structure

```
frontend/src/
  app/
    (dashboard)/        # Role-gated pages (trainer/*, participant/*)
    api/
      auth/             # Next.js route handlers for login/logout/register/me
      v1/[...path]/     # Generic BFF proxy → API Gateway
  components/           # UI components (shadcn/ui base in components/ui/)
  lib/
    api/                # Client-side fetch wrappers (calls /api/* BFF routes)
    auth/useAuth.ts     # Auth hook
    session.ts          # JWT decode + getSession() (server-only)
  middleware.ts         # Edge middleware: cookie auth + role-based route guards
```

The frontend uses **shadcn/ui** (Radix + Tailwind v4). All API calls from the browser go through Next.js API routes (BFF pattern); browser code never calls the gateway directly.

## CI

`.github/workflows/ci-pipeline.yml` runs on every push/PR to `main`:
- **Backend**: matrix over all 4 services — installs from `services/<name>/src/`, runs pytest if a `tests/` directory exists.
- **Frontend**: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm build`, `pnpm test --if-present`.
- The `JWT_SECRET` repo secret must be configured for backend CI to pass.

## Nginx

`nginx/nginx.conf` is intentionally a stub (returns 502). Wiring Nginx routes to the backend services is a candidate exercise (W2 D6 task).

## Incomplete service

`services/reporting-and-analytics-service/` is an empty placeholder — a candidate exercise (W2 D10 task).
