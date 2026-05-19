# CLAUDE.md

Guidance for working on this repository with Claude Code (claude.ai/code).

## Project Overview

**rev-eval** is the PEP cohort brownfield substrate — a local-first
multi-service assessment platform derived from `Revature/rev-eval-ai`
by stripping the Phase 2 AI surface.

**What candidates build on:**

- A trimmed Next.js + FastAPI substrate with auth, tests, questions,
  and submissions wired end-to-end.
- A docker-compose stack that brings everything up with `docker compose
  up --build` against Postgres + Mongo + MinIO + Nginx + 4 backends +
  the frontend.
- A CI pipeline (`.github/workflows/ci-pipeline.yml`) seeded with five
  realistic failures that candidates diagnose on W1 D3 and fix on W1 D4.

**What's deliberately missing** (candidate work, per `PEP_4Week_DailyTopics_v3.md`):

- Image upload endpoint on question-management (MinIO is wired, the
  endpoint is not — W2 D8)
- Nginx routing (config returns 502 stub — W2 D6)
- `reporting-and-analytics-service/` is empty (W2 D10)
- Test-taking pages (MCQ on W3 D13–D14; results view on W4 D17)
- Admin reports (W4 D19)
- Trivy + Ruff in CI (W2 D7)

## Architecture

### Monorepo

```
rev-eval/
├── frontend/                          # Next.js 16 (port 3000)
├── services/
│   ├── api-gateway-service/           # JWT verify + routing (port 8000)
│   ├── user-service/                  # Auth + users (port 8002, Postgres)
│   ├── question-management-service/   # Questions (port 8003, Mongo, MinIO)
│   ├── test-management-service/       # Tests + submissions (port 8001, Postgres)
│   └── reporting-and-analytics-service/  # Empty — candidates build
├── nginx/nginx.conf                   # Reverse-proxy stub (W2 D6 target)
├── docker-compose.yml                 # Local-first stack
└── .github/workflows/ci-pipeline.yml  # Build + test (no deploy)
```

### Technology Stack

**Backend:** Python 3.11 + FastAPI + Uvicorn + Pydantic. SQLAlchemy
(sync) for user-service; SQLAlchemy async + asyncpg for
test-management. PyMongo + Beanie + Motor for question-management.

**Frontend:** Next.js 16 (App Router) + React 19 + TypeScript +
Tailwind + shadcn/ui (Radix primitives). pnpm package manager.

**Auth:** HS256 JWT via `pyjwt`; password hashing via `passlib[bcrypt]`.
Frontend stores the token in an httpOnly cookie named `auth_token`
(no `localStorage`). The frontend uses `jose` for Edge-runtime-safe
JWT decoding in middleware. **The frontend never crypto-verifies** —
the gateway is the source of truth on every API call.

**Infra (local):** Postgres 15, Mongo 7, MinIO, Nginx, all in
docker-compose with named volumes and healthchecks.

## Common commands

```bash
# Bring the whole stack up
docker compose up --build

# Tear down (preserves volumes)
docker compose down

# Tear down + wipe volumes (forces seed re-run on next up)
docker compose down -v

# Logs for one service
docker compose logs -f user-service

# Run frontend lint / build / dev locally (against running backend stack)
cd frontend
pnpm install
pnpm lint
pnpm build
pnpm dev

# Backend service iteration (outside compose)
cd services/<svc>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port <port>
```

## API Gateway

`services/api-gateway-service/main.py` does pattern-based routing —
no service name in the URL. Routes:

```python
ROUTES = [
    {"pattern": r"^/v1/api/users(/.*)?$",      "service": "user-service"},
    {"pattern": r"^/v1/api/dashboard(/.*)?$",  "service": "test-management-service"},
    {"pattern": r"^/v1/api/tests(/.*)?$",      "service": "test-management-service"},
    {"pattern": r"^/v1/api/submissions(/.*)?$","service": "test-management-service"},
    {"pattern": r"^/v1/api/skills(/.*)?$",     "service": "test-management-service"},
    {"pattern": r"^/v1/api/questions(/.*)?$",  "service": "question-management-service"},
]
```

The gateway:
1. Verifies the Bearer JWT against `JWT_SECRET` env (HS256).
2. Extracts `sub`, `email`, `role` from claims.
3. Injects `X-User-Id`, `X-User-Email`, `X-User-Role` headers downstream.
4. Forwards via httpx; preserves query params + body.

Service discovery is compose-internal DNS — `http://user-service:8002`
resolves from any container in the network.

## Authentication

**user-service** exposes:

- `POST /v1/api/auth/register` — email + password (+ optional full_name, role)
- `POST /v1/api/auth/login` — email + password → JWT
- `GET /v1/api/auth/me` — Bearer-protected, returns user profile

Token claims: `sub=str(user.id)`, `email`, `role`, `exp`.

**Frontend** has matching BFF routes that set / read an httpOnly cookie:

- `POST /api/auth/register` → forwards to user-service, stores cookie
- `POST /api/auth/login` → same
- `POST /api/auth/logout` → clears cookie
- `GET /api/auth/me` → reads cookie, fetches profile via gateway

`useAuth()` (`frontend/src/lib/auth/useAuth.ts`) is a client hook that
hydrates from `/api/auth/me`. `getSession()` (`frontend/src/lib/session.ts`)
is the server-side equivalent.

## Microservices Detail

### user-service (port 8002)

PostgreSQL + SQLAlchemy. Models: `User(id, email, password_hash,
full_name, first_name, last_name, role: UserRole, is_active,
organization_id, created_at, updated_at, last_login)`. UserRole enum:
`TRAINER`, `PARTICIPANT`.

Tables are created on startup via `init_db()` — no Alembic.

### question-management-service (port 8003)

MongoDB + Beanie. `MONGO_URI` env (e.g.
`mongodb://admin:admin@mongo:27017/evalai?authSource=admin`) takes
precedence over the Atlas-style component fields when set.

`src/utils/s3_client.py` exposes a MinIO-aware boto3 client plus
`ensure_bucket()`, `generate_presigned_put_url()`, and
`generate_presigned_get_url()` helpers — wire these into an image-upload
endpoint on W2 D8.

### test-management-service (port 8001)

PostgreSQL + SQLAlchemy async (asyncpg). Models: `Test`, `Skill`,
`TestSubmission`. Uses Alembic-style structure but `init_db()` /
`Base.metadata.create_all` for table creation on first start.

`seed_db.py` is run by the container's `start.sh` after table creation;
it inserts 2 trainers + 5 participants (all share password
`password123`) + 6 demo tests + a skills catalogue + sample submissions.

`src/utils/dependencies.py` provides `get_current_user_from_headers`
(reads `X-User-Id`/`X-User-Email` set by the gateway, fetches the full
record from user-service), plus role-gated variants
`get_current_trainer` and `get_current_participant`.

### api-gateway-service (port 8000)

See above. No persistence.

### reporting-and-analytics-service

Empty service directory. Candidates create on W2 D10 — likely
`/v1/api/reports/*` patterns routed through the gateway.

## Frontend

Routes under `(dashboard)` are role-protected via the middleware
(`src/middleware.ts`):

- `/trainer/*` → TRAINER / ADMIN roles
- `/participant/*` → PARTICIPANT role
- `/dashboard` → auto-redirect based on role

Public:

- `/` — landing + login/register form
- `/unauthorized` — access-denied page

The BFF proxy at `frontend/src/app/api/v1/[...path]/route.ts` forwards
any frontend-side `/api/v1/*` call to the gateway with the cookie's
JWT attached as a Bearer token.

`useUserProfile()` is not yet present; use `useAuth()` from
`@/lib/auth/useAuth`.

## Environment

`.env.example` is the source of truth. Required for `docker compose up`:

```
JWT_SECRET=change-me-in-production
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
MONGO_USER, MONGODB_PASSWORD, MONGO_DB
S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME
```

The repo-root `.env` is gitignored. Do not commit secrets.

## Testing

Backend services have no `tests/` directories yet — CI skips pytest
when absent. Frontend has no test runner wired (`pnpm test --if-present`
short-circuits). Add tests as part of feature work; the CI pipeline
will pick them up automatically.

## Trainer / candidate context

Day-1 starting state is the `v0-day1-start` tag on `main`. The
`trainer/reference` branch tracks the trainer's working
implementation 1–2 days ahead of the cohort. End-of-week solution
branches will be cut as `solutions/week-N` from the corresponding
`trainer/reference` commit.

## What's deliberately stripped (history)

If you're tempted to add any of these back, check `PEP_rev-eval-ai_ScopeMap_v0.md`
and `PEP_BrownfieldStrip_v3.md` in the curriculum workspace first:

- WorkOS / AuthKit  → replaced by local JWT + bcrypt
- HashiCorp Consul  → replaced by compose-internal DNS
- AWS Cloud Map     → same
- AWS S3 + boto3 against real S3  → MinIO endpoint override
- AWS SQS + SES + notification-service  → out of scope
- AWS Lambda (interview-evaluator, quiz-evaluation-handler)  → out of scope
- AWS Bedrock + LangChain + LangGraph + LangSmith  → Phase 2
- ElevenLabs voice synthesis  → Phase 2
- three / @react-three (3D interview avatar)  → Phase 2
- Terraform (deploy/terraform/*)  → PEP delivers via GitHub Actions only
- AWS ECS deploy workflows  → PEP is local-first

Each removal is documented in its commit message.
