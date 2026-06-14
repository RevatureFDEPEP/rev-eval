# Security hardening — authz, JWT secrets, gateway routing (W5)

**Branch:** `jor-w5-sec-auth-secrets` · **Priority:** RED / P0

Closes privilege-escalation, unauthenticated-enumeration, IDOR, weak-JWT,
unsafe-secret, and infrastructure-exposure risks. This document records the
confirmed findings, the implementation decisions, the before/after behavior,
and how it was verified.

---

## Confirmed findings (validated against the live repo)

| # | Finding | Evidence (before) |
|---|---------|-------------------|
| 1 | User routes had **no authorization** | `user_route.py`: PATCH/GET/list/by-email/invite used only `Depends(get_db)`; `update_user` wrote `role`/`is_active` from the body unconditionally. |
| 2 | Legacy gateway route was **unauthenticated** | `main.py` `legacy_gateway` (`/{service}/{path}`) had no `verify_jwt_token`; reachable downstream reads enabled user enumeration. No callers (grep). |
| 3 | Test/skill/submission **writes unprotected**; submission **IDOR** | `test_submission_route.py` get/update/delete had no ownership/role checks; `list` honored `?user_id` for anyone; `skill_route.py` fully open. |
| 4 | Question **mutations unprotected** | `question_routes.py` create/update/delete had no role guard. |
| 5 | **Weak JWT validation** | gateway + user-service decoded with signature+exp only — no `iss`/`aud`/`nbf`, no required role. |
| 6 | **Unsafe secret accepted** | `JWT_SECRET` defaulted to `change-me-in-production`; only emptiness was rejected. |
| 7 | No **login rate limiting**; weak TLS/headers | `nginx.conf` had no `limit_req`, no TLS pinning, no security headers; `X-Forwarded-For` appended client value (spoofable). |
| 8 | **Infrastructure exposure** | Postgres/Mongo/MinIO/observability bound `0.0.0.0`. |

**Already fixed / not found:** internal app-service ports were already
loopback-bound; client `X-User-*` spoofing was already stripped at the gateway.

**Adjustment to the plan:** the `UserRole` enum lacked `ADMIN` (only
`TRAINER`/`PARTICIPANT`). Added `ADMIN` so admin authorization is meaningful.

---

## Implementation by phase

### Phase 1 — user-service authorization
- Added `get_current_admin`, `get_current_admin_or_self`, and internal-key
  variants (`get_admin_or_internal`, `get_admin_or_self_or_internal`) plus
  `is_admin`.
- `GET /users/`, `POST /users/invite`, `GET /users/by-email` → admin (or
  trusted internal). `GET /users/{id}` and `PATCH /users/{id}` → admin-or-self.
- Field-level lock: a non-admin self-update cannot change `role` or `is_active`.
- Added `ADMIN` to `UserRole`.
- **Internal-key bypass:** test-management calls user-service directly
  (no JWT). An `X-Internal-Key` shared secret lets those server-to-server reads
  pass the admin guards. The gateway strips any client-supplied `X-Internal-Key`
  (and `X-User-*`), so it can never be forged from outside the network.

### Phase 2 — gateway legacy route
- Removed the unauthenticated `/{service}/{path}` route. Such requests now fall
  through to the JWT-guarded smart route → `401` when unauthenticated.
- `strip_client_identity_headers` now also drops `X-Internal-Key`.

### Phase 3 — test-management authz + submission IDOR
- Centralized `get_current_trainer_or_admin`, `get_current_admin`, `role_of`,
  `is_admin`, `is_trainer`, `ensure_can_access_submission`.
- Test/skill create/update/delete → trainer/admin (admin bypasses creator
  ownership on tests).
- Submissions: `GET /{id}` ownership-or-privileged; `list` pins participants to
  their own and rejects `?user_id=other`; update/delete → trainer/admin; create
  restricts participants to their own `user_id`. Trainer-review/bulk-assign
  endpoints require trainer/admin (were any-authenticated).

### Phase 3b — question mutations
- `require_question_editor` (reads gateway-verified `X-User-Role`): `401`
  role-less, `403` non-editor. Applied to create/update/delete. Reads stay open.

### Phase 4 — JWT claims + secret fail-fast
- Issued tokens now carry `sub/email/role/iss/aud/iat/nbf/exp`.
- Gateway and user-service verify signature, algorithm, expiry, not-before,
  issued-at, issuer, audience, subject, and a **known role** claim.
- `validate_jwt_secret` rejects missing/placeholder/short secrets at startup;
  `ALLOW_INSECURE_DEV_SECRETS=true` is the local-dev escape hatch.
- New settings: `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_MIN_SECRET_LENGTH`,
  `ALLOW_INSECURE_DEV_SECRETS`, `INTERNAL_API_KEY`.

### Phase 5 — Nginx
- `limit_req_zone … rate=5r/m` on `/api/v1/api/auth/(login|register)`,
  `limit_req_status 429`.
- TLS 1.2/1.3 + modern ciphers, `ssl_session_*`, HSTS, `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`. `client_max_body_size`, proxy
  timeouts. `X-Forwarded-For` set to the real peer addr (no client spoofing).
- CSP intentionally deferred pending Next.js validation.

### Phase 6 — compose exposure
- Postgres/Mongo/MinIO/Loki/Grafana/Alloy and app/gateway/frontend host ports
  bound to `127.0.0.1`; only Nginx (`:80`/`:443`) is exposed off-host.
  `localhost` access for local dev is preserved.
- `.env.example` documents credential rotation and new variables.

---

## Behavior: before → after

- Anonymous `GET /v1/api/users/` → 200 list → **401/403**.
- Participant `PATCH /users/{self}` with `role=ADMIN` → applied → **403**.
- `GET /user-service/v1/api/users/` (legacy) → 200 → **401**.
- Participant `GET /v1/api/submissions/5` (not owner) → 200 → **403**.
- Participant `GET /v1/api/submissions?user_id=other` → other's data → **403**.
- Anonymous `POST /v1/api/questions` → 201 → **401**.
- Token without `aud`/`iss`/`nbf`/role → accepted → **401**.
- `JWT_SECRET=change-me-in-production` (no escape hatch) → ran → **startup fails**.
- Spoofed `X-User-Role: ADMIN` / `X-Internal-Key` from a client → **stripped**.

> **Compatibility note:** tokens issued before deploy lack the new claims and
> are rejected; clients re-authenticate once (60-min token TTL).

---

## Changed files

- `services/user-service/`: `models/user.py`, `config/settings.py`,
  `services/auth_service.py`, `utils/dependencies.py`, `v1/routes/user_route.py`,
  `main.py`, tests `test_user_authz.py`, `test_jwt_hardening.py`.
- `services/api-gateway-service/`: `main.py`, `src/middleware/auth.py`,
  tests `test_gateway_routing_and_auth.py`.
- `services/test-management-service/`: `config/settings.py`, `utils/dependencies.py`,
  `services/test_submission_service.py`, `v1/routes/{test_route,skill_route,test_submission_route}.py`,
  tests `test_authz_submission_idor.py` (+ fake-client signature fix).
- `services/question-management-service/`: `utils/dependencies.py`,
  `v1/routes/question_routes.py`, tests `test_question_write_authz.py`.
- `nginx/nginx.conf`, `docker-compose.yml`, `.env.example`.

---

## Verification

```
pytest services/user-service/tests              # 43 passed
pytest services/api-gateway-service/tests        # 22 passed
pytest services/test-management-service/tests     # 73 passed
pytest services/question-management-service/tests # 42 passed
ruff check services/...                          # clean
docker compose config                            # valid
docker run --rm -v nginx.conf -v certs nginx -t  # syntax ok
```

## Deferred (out of scope)

- Content-Security-Policy (needs Next.js validation).
- Asymmetric JWT signing, account lockout/audit, production WAF.
- Removing dev credential fallbacks from compose (kept for local-first DX;
  documented as must-rotate, and the JWT secret already fails fast).
- Trainer-review endpoints allow any trainer to review any submission — this is
  the existing product decision (`get_evaluated_submissions_for_trainer`), now
  at least restricted to trainer/admin.
