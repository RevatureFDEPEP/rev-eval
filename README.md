# rev-eval

Revature Evaluation Platform — PEP brownfield substrate.

Local-first multi-service application:
- **FastAPI** microservices (Python 3.11)
- **Next.js 16** frontend (React 19, TypeScript)
- **PostgreSQL 15** + **MongoDB 7** for persistence
- **MinIO** for S3-compatible object storage
- **Nginx** reverse proxy (candidates wire routes on W2 D6)

---

## Quick start

You need Docker (or Colima / Docker Desktop) running.

```bash
cp .env.example .env             # adjust JWT_SECRET, secrets if needed
docker compose up --build
```

Once the stack is healthy:

| URL | What |
|-----|------|
| http://localhost:3000 | Frontend (Next.js, login / dashboards) |
| http://localhost:8000/health | API gateway health |
| http://localhost:8000/routes | Configured routing table |
| http://localhost:8001/docs | test-management-service Swagger |
| http://localhost:8002/docs | user-service Swagger |
| http://localhost:8003/docs | question-management-service Swagger |
| http://localhost:9001 | MinIO console (`minioadmin` / `minioadmin`) |
| http://localhost | Nginx — returns 502 by design (W2 D6 target) |

Default seeded users share password `password123` (see
`services/test-management-service/seed_db.py`).

---

## Services in scope

| Path | Service | Port | DB |
|------|---------|------|----|
| `services/user-service/` | Auth + users (JWT + bcrypt) | 8002 | Postgres |
| `services/question-management-service/` | Question bank + MinIO uploads | 8003 | Mongo |
| `services/test-management-service/` | Tests, skills, submissions | 8001 | Postgres |
| `services/api-gateway-service/` | JWT verify + request routing | 8000 | — |
| `services/reporting-and-analytics-service/` | (empty — W2 D10 candidate task) | — | — |

`frontend/` is the Next.js app. Authentication is a local POST to
user-service that issues a HS256 JWT stored in an httpOnly cookie; the
gateway verifies the cookie's JWT on each request and forwards
`X-User-Id`, `X-User-Email`, `X-User-Role` to downstream services.

## CI

`.github/workflows/ci-pipeline.yml` runs build + test for the four
backend services (matrix) and the frontend on every push / PR to
`main`.
