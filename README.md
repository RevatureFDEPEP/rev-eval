# Rev-Eval

A multi-service skills assessment platform. Trainers create and assign tests, participants take them under a timer, and the system scores each submission and reports analytics.

This was a team Forward Deployed Engineering (FDE) project that started from a partially built, brownfield codebase. **This is the `kalabek` integration branch, which holds one contributor's work** (Kalabe Kebede); the organization's `main` branch does not contain it.

## What this branch adds

- **Scoring engine** with idempotent submissions and row locking, so a retried or concurrent submit cannot double-score
- **Timed quiz experience**: polymorphic question rendering, a timer, autosave and a submit state machine
- **Reporting & Analytics service**: a working FastAPI service with Alembic migrations, per-test reports, aggregates, per-question statistics, rankings and per-user attempt history, reading the shared Postgres directly (see its ADR 0001)
- **Authentication and authorization**: JWT verification at the gateway, service-level role checks (`TRAINER`, `PARTICIPANT`) and signature verification in the frontend middleware
- **Routing and traceability**: Nginx and gateway routing across all services, and `X-Request-Id` propagation for tracing across services
- **Testing and CI**: PostgreSQL integration tests, frontend tests and an optional Playwright end-to-end run

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI microservices (Python 3.11 images) |
| Frontend | Next.js 16, React 19, TypeScript, Vitest |
| Data | PostgreSQL 15, MongoDB 7, MinIO (S3-compatible object storage) |
| Edge | Nginx reverse proxy with TLS, plus a JWT-verifying API gateway |
| Delivery | Docker Compose, GitHub Actions |

## Architecture

```
Browser
  ↓
Nginx            HTTP→HTTPS redirect, rate limiting, security headers, gzip
  ├── pages ──────→ Next.js frontend
  └── /v1/api/* ──→ API gateway    verifies the JWT cookie, forwards identity headers
                       ↓
   ┌───────────────┬──────────────────────────┬─────────────────────────────┬────────────────────────────────┐
   user-service    test-management-service    question-management-service   reporting-and-analytics-service
   (Postgres)      (Postgres)                 (MongoDB + MinIO)             (read-only queries on the shared Postgres)
```

The login flow is a POST to `user-service`, which issues an HS256 JWT stored in an httpOnly cookie. The gateway verifies it on every request and forwards `X-User-Id`, `X-User-Email` and `X-User-Role` to the downstream services.

## Services

| Path | Service | Port | Storage |
|------|---------|------|---------|
| `services/api-gateway-service/` | JWT verification and request routing | 8000 | none |
| `services/test-management-service/` | Tests, skills, test sessions, submissions and scoring | 8001 | PostgreSQL |
| `services/user-service/` | Authentication and users (JWT, bcrypt) | 8002 | PostgreSQL |
| `services/question-management-service/` | Question bank and file uploads | 8003 | MongoDB, MinIO |
| `services/reporting-and-analytics-service/` | Reports, aggregates, rankings and attempt history | 8004 | PostgreSQL |
| `frontend/` | Next.js app (trainer and participant UI) | 3000 | none |

The gateway routes `/v1/api/auth`, `users`, `dashboard`, `tests`, `submissions`, `skills`, `questions`, `test-sessions` and `reports` to the services above.

## Run locally

You need Docker (Docker Desktop or Colima).

```bash
cp .env.example .env     # review the values; they are local development defaults
docker compose up --build
```

| URL | What |
|-----|------|
| https://localhost | Nginx front door (self-signed certificate generated on first start; HTTP on port 80 redirects here) |
| http://localhost:3000 | Frontend directly |
| http://localhost:8000/health | Gateway health |
| http://localhost:8000/routes | Gateway routing table |
| http://localhost:8001/docs, 8002/docs, 8003/docs | Swagger UI for the test, user and question services |
| http://localhost:9001 | MinIO console |

Synthetic demo users and sample tests are seeded for local development by `services/test-management-service/seed_db.py`. Local credentials for the demo accounts, MinIO and the databases come from `.env.example` and that script; they are development defaults only, so change them before running anywhere beyond your own machine.

A quick health check of every service: `./scripts/smoke.sh`.

## Testing and CI

`.github/workflows/ci-pipeline.yml` runs on every push, on pull requests, and on manual dispatch:

- **Backend, one job per service** (user, question-management, test-management, api-gateway, reporting-and-analytics), with PostgreSQL 15 and MongoDB 7 service containers: `ruff` lint, `pytest` with coverage, and a **diff-coverage gate of 80 % on changed lines**
- **Trivy** filesystem scan of each service, failing on fixed CRITICAL or HIGH findings
- **Frontend**: lint with zero warnings, production build, build-provenance attestation, and `vitest`
- **Playwright end-to-end** (`e2e/`): runs only when started manually with `run_e2e=true`, because it needs the full stack
- A final **CI Gate** job that fails if the backend, frontend or Trivy jobs fail

## Scope

A local, team-built training project with seeded demo data. It is not deployed anywhere, and no compliance or certification is claimed.
