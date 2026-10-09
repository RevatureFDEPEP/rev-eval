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
- **Registration is participant-only.** `/auth/register` always stores a `PARTICIPANT`; a request for any other role gets 403 and creates nothing. Trainer accounts are provisioned through a trusted path (`seed_db.py` in test-management, or a direct database insert).

## Who can call what

Every `/users/*` route resolves the caller from the signed Bearer JWT, not from forwarded `X-User-*` headers. A missing or invalid token, or an inactive account, gets 401; a forbidden request gets 403 and changes nothing.

| Route | Participant | Trainer |
|-------|-------------|---------|
| `GET /users/me` | own record | own record |
| `GET /users/{user_id}`, `GET /users/by-email/{email}` | own record only | any user |
| `GET /users/` | 403 | allowed |
| `POST /users/invite` | 403 | participant accounts only |
| `PATCH /users/{user_id}` | own first and last name only | own first and last name only |

No one can change an account's email, role or active status through the API. test-management-service calls these routes with the caller's own forwarded token, so the same rules apply to it.

These rules, and participant-only registration, are implemented in [#173](https://github.com/RevatureFDEPEP/rev-eval/pull/173); merge it before this README.

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). Configuration is read from environment variables: `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`, `JWT_SECRET` (must match the gateway's), `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` and `ALLOW_ORIGINS`.

```bash
cd services/user-service
pip install -r requirements.txt pytest pytest-cov
pytest        # fails below 80 % coverage
```

The unit tests run against SQLite. The Postgres integration tests run only when `CI=true`, against the CI database service.
