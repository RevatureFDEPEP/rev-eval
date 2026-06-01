# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Full stack (recommended)
```bash
cp .env.example .env          # once; adjust JWT_SECRET if needed
docker compose up --build
```

### Frontend only
```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:3000 (Turbopack)
pnpm lint
pnpm build
```

### Backend service (local, no Docker)
Each service's `requirements.txt` lives in `services/<name>/src/`:
```bash
cd services/<service-name>
pip install -r src/requirements.txt
uvicorn main:app --reload --port <port>
```

### Backend tests
```bash
cd services/<service-name>
pytest --cov                                    # all tests
pytest tests/path/to/test_file.py::test_name   # single test
```

## Architecture

### Service map

| Service | Port | DB | Purpose |
|---------|------|----|---------|
| `api-gateway-service` | 8000 | — | JWT verification + pattern-based routing |
| `test-management-service` | 8001 | PostgreSQL | Tests, skills, submissions, dashboard |
| `user-service` | 8002 | PostgreSQL | Auth (login/register), user management |
| `question-management-service` | 8003 | MongoDB | Question bank, MinIO image uploads |
| `reporting-and-analytics-service` | — | — | Empty — candidate implementation task (W2 D10) |

### Auth flow

1. Frontend `POST /v1/api/auth/login` → API gateway passes through (no JWT check) → user-service issues HS256 JWT stored as `auth_token` httpOnly cookie.
2. All subsequent requests: Next.js middleware (`frontend/src/middleware.ts`) decodes the cookie client-side for role-based redirects, while the API gateway independently verifies the JWT server-side.
3. Gateway injects `X-User-Id`, `X-User-Email`, `X-User-Role` headers; downstream services read these instead of re-verifying tokens.

### Gateway routing

`api-gateway-service/main.py` matches request paths by regex against `ROUTES`:
- `/v1/api/auth/*` — user-service, **public** (no JWT required)
- `/v1/api/users/*` — user-service
- `/v1/api/dashboard/*`, `/v1/api/tests/*`, `/v1/api/submissions/*`, `/v1/api/skills/*` — test-management-service
- `/v1/api/questions/*` — question-management-service

A legacy route format (`/<service-name>/<path>`) also exists but bypasses JWT.

### Backend layer pattern

All FastAPI services follow the same layered structure:
```
src/config/settings.py   → pydantic-settings env loading
src/db/session.py        → DB engine (SQLAlchemy or Motor/Beanie)
src/models/              → ORM models (SQLAlchemy for Postgres; Beanie Documents for Mongo)
src/repositories/        → CRUD / query logic only
src/services/            → business logic, coordinates repositories
src/v1/routes/           → FastAPI routers, registered in main.py
```

### Frontend structure

- `frontend/src/app/` — Next.js App Router; `/trainer/*` and `/participant/*` are role-gated
- `frontend/src/middleware.ts` — JWT decode (via `jose`) + role-based redirect; roles: `TRAINER`, `PARTICIPANT`, `ADMIN`
- `frontend/src/lib/api/` — typed API client functions (one file per domain: `client.ts`, `tests.ts`, `questions.ts`, `submissions.ts`, `quiz-sessions.ts`)
- `frontend/src/lib/auth/useAuth.ts` — auth hook used throughout the app

### Data stores

- **PostgreSQL**: user-service and test-management-service use SQLAlchemy 2.x async sessions.
- **MongoDB**: question-management-service uses Beanie ODM (Motor async driver).
- **MinIO**: question-management-service uploads question images to S3-compatible object storage (default credentials `minioadmin`/`minioadmin`, console at http://localhost:9001).

### Seeded test users

Default password for all seeded users: `password123`. See `services/test-management-service/seed_db.py` for accounts.

### Nginx

Currently returns 502 by design — candidates wire routes in W2 D6.
