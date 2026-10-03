# API Gateway Service

The single entry point for backend API traffic. A FastAPI service on port **8000**.

## What it does

- **Verifies the JWT** on every request except login and registration (`/v1/api/auth/login`, `/v1/api/auth/register`, which pass through to `user-service`). It expects a Bearer token in the `Authorization` header; the Next.js server adds that header from the session cookie.
- **Forwards identity** to downstream services as `X-User-Id`, `X-User-Email` and `X-User-Role` headers, so services act on the verified identity rather than anything the client sends.
- **Routes** `/v1/api/*` to the owning service by path prefix: `auth` and `users` to user-service; `tests`, `submissions`, `skills`, `dashboard` and `test-sessions` to test-management-service; `questions` to question-management-service; and `reports` to reporting-and-analytics-service.
- **Propagates `X-Request-Id`**: it accepts the incoming value or generates one, returns it on the response and passes it to the downstream service, so a request can be followed across services.
- Exposes `GET /health` and `GET /routes` (the configured routing table).

It stores no data. Authorization beyond "valid token" is enforced again inside the services by role.

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). To run its tests:

```bash
cd services/api-gateway-service
pip install -r requirements.txt pytest pytest-cov httpx
pytest        # fails below 80 % coverage
```

Configuration is read from environment variables; `JWT_SECRET` must match the one used by `user-service`.
