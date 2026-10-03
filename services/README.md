# Rev-Eval Services

The five FastAPI backend services behind the Rev-Eval assessment platform. Each directory is an independent service with its own `Dockerfile`, `requirements.txt` and tests.

| Service | Responsibility | Storage | Port |
|---------|----------------|---------|------|
| `api-gateway-service/` | Verifies the Bearer JWT, forwards identity headers (`X-User-Id`, `X-User-Email`, `X-User-Role`) and routes `/v1/api/*` to the services below | none | 8000 |
| `test-management-service/` | Tests, skills, test sessions, submissions and scoring | PostgreSQL | 8001 |
| `user-service/` | Registration, login and users (JWT, bcrypt) | PostgreSQL | 8002 |
| `question-management-service/` | Question bank and file uploads | MongoDB, MinIO | 8003 |
| `reporting-and-analytics-service/` | Reports, aggregates, rankings and attempt history; reads the shared PostgreSQL ([ADR 0001](reporting-and-analytics-service/adr/0001-direct-db-read.md)) | PostgreSQL | 8004 |

The Next.js app is in [`../frontend/`](../frontend/) and the Nginx edge configuration in [`../nginx/`](../nginx/). For the architecture diagram, how to run the stack locally, and what CI checks, see the [root README](../README.md).
