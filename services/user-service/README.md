# User Service

A FastAPI service on port **8002** that owns user accounts and issues the JWTs the rest of the platform trusts. Users are stored in PostgreSQL (SQLAlchemy); the `users` table is created on startup.

## Responsibilities

| Area | Routes (under `/v1/api`) |
|------|--------------------------|
| Registration and login | `/auth/register`, `/auth/login` |
| Current user | `/auth/me`, `/users/me` |
| Users | `/users/` (list, filter by role), `/users/{user_id}`, `/users/by-email/{email}`, `PATCH /users/{user_id}` |
| Invitations | `/users/invite` |

It also exposes `GET /health`.

## How authentication behaves

- **Passwords** are hashed with bcrypt (passlib); registration requires 8 to 128 characters.
- **Tokens:** register and login return an HS256 JWT carrying the user's id (`sub`), email and role, valid for `JWT_EXPIRY_MINUTES` (60 by default).
- **Current user:** `/auth/me` and `/users/me` read the Bearer token, verify it and return the user; an invalid or expired token, or an inactive user, gets 401.
- **Invitations** create an inactive user with no password; login is refused for that account.

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). Configuration is read from environment variables: `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`, `JWT_SECRET` (must match the gateway's), `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` and `ALLOW_ORIGINS`.

```bash
cd services/user-service
pip install -r requirements.txt pytest pytest-cov
pytest        # fails below 80 % coverage
```

The unit tests run against SQLite. The Postgres integration tests run only when `CI=true`, against the CI database service.
