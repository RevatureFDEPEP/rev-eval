# Rev-Eval

**Skills Assessment & Analytics Platform.** Trainers build and assign tests, participants take them under a timer, and FastAPI microservices behind an Nginx TLS edge and a JWT-verifying API gateway score each submission exactly once and turn the results into reports and rankings.

[![CI Pipeline](https://github.com/RevatureFDEPEP/rev-eval/actions/workflows/ci-pipeline.yml/badge.svg?branch=kalabek)](https://github.com/RevatureFDEPEP/rev-eval/actions/workflows/ci-pipeline.yml?query=branch%3Akalabek)

The `kalabek` integration branch contains Kalabe Kebede's implemented Rev-Eval contributions.

## What it demonstrates

- **Microservices behind one edge**: Nginx terminates TLS in front of a Next.js BFF and a FastAPI API gateway that routes to four domain services
- **Correct scoring under retries and races**: row-level locking (`SELECT ... FOR UPDATE`) plus SHA-256-hashed idempotency keys, tested against real PostgreSQL
- **Layered authentication and authorization**: JWT in an httpOnly cookie, verified in the Next.js middleware and at the gateway; user-service and test-management verify it again and enforce role and ownership rules from it
- **Polyglot persistence**: PostgreSQL for users, tests and sessions; MongoDB for the question bank; MinIO object storage through presigned URLs
- **Reporting and analytics**: per-test reports, aggregates, per-question statistics, rankings and attempt history from a dedicated service
- **CI/CD quality gates**: per-service lint, tests and an 80 % diff-coverage gate, Trivy scans, a zero-warning frontend build and build-provenance attestation

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/rev-eval-architecture-dark.svg">
  <img src="docs/diagrams/rev-eval-architecture.svg" alt="Rev-Eval logical architecture. Trainers and participants reach Nginx over HTTPS. Nginx terminates TLS, redirects HTTP to HTTPS, rate-limits the API path and adds security headers, then forwards pages and BFF calls to the Next.js frontend and /v1/api calls to the API gateway. The Next.js BFF reads the JWT from an httpOnly cookie and calls the gateway with a Bearer token. Inside the private Docker network the gateway verifies the JWT and routes to user-service, test-management, reporting-and-analytics and question-management, forwarding identity headers and a request ID. User, test, session and score data live in PostgreSQL, which reporting reads with read-only queries; questions live in MongoDB and question images in MinIO. A cross-cutting operations strip shows Docker Compose and GitHub Actions CI with lint, tests, diff coverage, Trivy and the frontend build." width="1000">
</picture>

A browser request reaches **Nginx** over HTTPS. Pages and the Next.js `/api` routes go to the **frontend**, whose server-side BFF takes the JWT from an httpOnly cookie and calls the **API gateway** with a Bearer token; `/v1/api/*` goes to the gateway directly. The gateway verifies the token, picks the owning service by path prefix, and forwards the call on the private Docker network with the caller's identity and a request ID. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

<details>
<summary>Text version</summary>

```
Browser (trainer, participant)
  │ HTTPS
Nginx              TLS 1.2/1.3 · HTTP→HTTPS redirect · rate limit on /v1/api · security headers
  ├── pages, /api ──→ Next.js frontend + BFF   httpOnly JWT cookie → Bearer header
  │                         │ REST
  └── /v1/api/* ─────→ API gateway             verifies JWT · X-User-* · X-Request-Id
                            │ internal HTTP
   ┌──────────────┬─────────┴────────┬─────────────────────────┬─────────────────────┐
   user-service   test-management    reporting-and-analytics   question-management
   PostgreSQL     PostgreSQL         PostgreSQL (read-only)    MongoDB + MinIO
```

</details>

**Key design decisions**

- **Gateway plus BFF**: one API entry point for token verification and routing, and a BFF so the token never reaches browser JavaScript, at the cost of an extra hop.
- **Reporting reads the shared database**: aggregate SQL runs where the data lives instead of paging records over HTTP or running an event pipeline; the cost is schema coupling, recorded in [ADR 0001](services/reporting-and-analytics-service/adr/0001-direct-db-read.md).
- **Exactly-once scoring enforced by the database**: a row lock and a stored idempotency hash, not client behaviour, prevent double scoring.
- **One published edge**: the base Compose stack publishes only Nginx; services, databases and MinIO stay on the private network.

## Engineering highlights

| Area | Implementation |
|------|----------------|
| Scoring | Exact match for single-answer questions, Jaccard partial credit for multi-select |
| Idempotency | `Idempotency-Key` stored as a SHA-256 hash per test part; a retry replays the original result, a different key after finalization is rejected |
| Concurrency | Session row read with `SELECT ... FOR UPDATE` on submit, so concurrent submits serialize |
| Timed sessions | Polymorphic question rendering, timer, draft autosave and an explicit submit state machine in the frontend |
| Reporting | Per-test reports, aggregates, per-question statistics, rankings and paginated attempt history; Alembic-managed indexes |
| Object storage | Question images through time-limited presigned MinIO URLs, so image bytes bypass the service |
| Traceability | `X-Request-Id` accepted or generated at the gateway, forwarded to services and echoed on responses |

## Security & Trust Boundaries

The system is grouped into four zones: **public** (browsers), the **Nginx edge**, the **private Docker network** (frontend, gateway, services) and the **data layer**. Current controls:

- **TLS at the edge**: Nginx terminates TLS 1.2/1.3, redirects HTTP to HTTPS, and is the only container publishing host ports in the base stack.
- **JWT verification in depth**: the gateway verifies every token except on login and registration; the Next.js middleware verifies the session JWT before serving protected pages; user-service, test-management, reporting and question-management verify it again on every protected route.
- **httpOnly cookie through a BFF**: the token lives in an httpOnly cookie and is attached server-side as a Bearer header.
- **Service-level authorization**: user-service and test-management resolve the caller from their own verified JWT and enforce `TRAINER` / `PARTICIPANT` role and ownership rules: participants reach only their own account, submissions and quiz sessions, and trainers manage only the tests they created. The question bank in question-management is for trainers and for test-management's scoring calls only; participants receive just their own quiz session's questions, without answer keys.
- **Participant-only sign-up**: public registration always creates a participant; trainer accounts are provisioned through the seed script, not the API.
- **Trusted identity forwarding**: the gateway drops client-supplied `X-User-*` headers, sets them from the verified token, and adds an `X-Request-Id`.
- **Edge hardening**: rate limiting on `/v1/api/`, plus HSTS, `X-Frame-Options`, `X-Content-Type-Options` and `Referrer-Policy` headers.
- **Supply-chain checks**: a Trivy scan of every service in CI and build-provenance attestation for the frontend.

Traffic inside the private network is plain HTTP. Control details and known limits: [docs/SECURITY.md](docs/SECURITY.md).

## Reliability and observability

- Compose health checks gate startup in order: databases, then services, then the gateway, then Nginx.
- Submission retries and concurrent submits are safe by construction (idempotency hash plus row lock).
- Draft answers autosave during a timed session.
- Request IDs correlate a call across the gateway and services, and the gateway returns the ID to the caller.

## Testing

`.github/workflows/ci-pipeline.yml` runs on every push and pull request:

- **Backend matrix (five services)** with PostgreSQL 15 and MongoDB 7 service containers: `ruff`, `pytest` with coverage, and an **80 % diff-coverage gate on changed lines**. Includes PostgreSQL integration tests for authentication and the session row lock, and MongoDB integration tests for the question bank.
- **Trivy** filesystem scan per service, failing on fixed CRITICAL or HIGH findings.
- **Frontend**: ESLint with zero warnings, production build, build-provenance attestation, and Vitest (results chart, autosave, timer, submit state machine).
- **Playwright end-to-end** happy path (register, take a test, submit, see results) against the full Compose stack, on manual dispatch with `run_e2e=true`.
- **CI Gate** fails the run if the backend, frontend or Trivy jobs fail.

## Technology

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Vitest |
| Backend | FastAPI microservices, SQLAlchemy, Alembic, Beanie (MongoDB), PyJWT, bcrypt |
| Data | PostgreSQL 15, MongoDB 7, MinIO (S3-compatible) |
| Edge | Nginx (TLS, rate limiting, security headers), FastAPI API gateway |
| Delivery | Docker Compose, GitHub Actions, Trivy, Playwright |

## Project scope

Runs locally with seeded demo data.

## Run locally

You need Docker (Docker Desktop or Colima).

```bash
cp .env.example .env          # local development defaults (APP_ENV=development); change them before running anywhere else
docker compose up --build     # or ./start.sh, which also waits until Nginx is serving
```

Open **https://localhost** (a self-signed certificate is generated on first start; HTTP on port 80 redirects). Check the stack with `./scripts/smoke.sh` and stop it with `docker compose down` (add `-v` to remove the data volumes).

`services/test-management-service/seed_db.py` seeds synthetic demo users and sample tests. Their credentials, like the database and MinIO credentials in `.env.example`, are development defaults only.

### Developer endpoints

The base stack publishes only Nginx. For direct access to the services, databases and MinIO, add the development override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build   # or ./start.sh --dev
```

| Address | What |
|---------|------|
| http://localhost:3000 | Next.js dev server directly |
| http://localhost:8000/health, http://localhost:8000/routes | API gateway health and routing table |
| http://localhost:8001/docs, :8002/docs, :8003/docs, :8004/docs | Swagger UI: test-management, user, question-management, reporting |
| localhost:5432, localhost:27017 | PostgreSQL, MongoDB |
| http://localhost:9001 | MinIO console (S3 API on 9000) |

`./scripts/smoke.sh --direct` checks each service's `/health` on these ports, and the Playwright suite in [`e2e/`](e2e/) uses the frontend and gateway ports.

## Documentation

- [Architecture](docs/ARCHITECTURE.md): request flow, routing table, data ownership, scoring and design decisions
- [Security](docs/SECURITY.md): trust boundaries, controls and known limits
- [ADR 0001: reporting data access](services/reporting-and-analytics-service/adr/0001-direct-db-read.md)
- Service READMEs: [overview](services/README.md), [API gateway](services/api-gateway-service/README.md), [user](services/user-service/README.md), [test management](services/test-management-service/README.md), [question management](services/question-management-service/README.md), [reporting and analytics](services/reporting-and-analytics-service/README.md), [frontend](frontend/README.md)
