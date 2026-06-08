# W3-F1 — Quiz Session Creation Backend

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §1 (Day 11)
**Depends on:** [W2-F7](w2-f7-alembic-category-domain.md) (sessions table is a new Alembic revision on test-management-service's schema), W2 Compose topology (question-management-service + Mongo must be healthy for the cross-service httpx call), [W2-F5](w2-f5-minio-presigned-uploads.md) (question bank must be seeded so `$sample` returns results)
**Unblocks:** W3-F2 (Scoring Engine — needs sessions table + `current_index` to lock and advance), W3-F3 (Frontend Skeleton — page calls `POST /sessions` server-side on load)
**Last updated:** 2026-06-08

Implement `POST /sessions` in test-management-service that mints an opaque
session token, records **server-authoritative** timing, and fetches the first
question from question-management-service over httpx. Establishes the
cross-service HTTP integration pattern (timeouts, bounded retries,
correlation-id propagation).

## Steps

- [ ] **1. Sessions table + migration** — `Session` model (`sessions`):
      `session_id` UUID PK, `test_id`, `user_id`, `session_token`, `server_now`,
      `expires_at`, `status` (active/submitted/expired), `current_index`.
      Generate via `alembic revision --autogenerate` as `0004` on the existing
      chain. Evidence: `services/test-management-service/src/models/session.py`,
      `alembic/versions/0004*.py`.
- [ ] **2. POST /sessions handler** — accept a quiz/test ID; mint `session_id`
      with `uuid4` and `session_token` with `secrets.token_hex`; compute
      `expires_at` server-side from `test.duration_seconds`; persist row
      **before** responding. Standard vertical slice: `session_schema.py`,
      `session_repository.py`, `session_service.py`,
      `v1/routes/session_route.py`.
- [ ] **3. Cross-service question fetch** — module-level `httpx.AsyncClient`
      singleton with explicit `timeout`. Call question-management-service to
      pull question IDs via MongoDB `$sample` aggregation and fetch the first
      question body. Bounded retries on transient failures.
- [ ] **4. Correlation-id propagation** — read/generate `X-Correlation-Id` on
      the inbound request and forward it on every outbound httpx call so
      distributed logs (W2-F3 Loki/Grafana) can be traced across services.
- [ ] **5. Response contract** — return `session_id`, `session_token`,
      `server_now`, `expires_at`, and the first question. Client never computes
      or stores timing. Lock the shape early — W3-F3 consumes it server-side.
- [ ] **6. Gateway route** — add `^/v1/api/sessions(/.*)?$` →
      test-management-service in `services/api-gateway-service/main.py`.

## Notes

- This is the first cross-service call in the platform — the
  `httpx.AsyncClient` singleton + timeout/retry/correlation-id pattern set here
  is reused by W3-F4's draft endpoint and the W4 reporting service.
- question-management-service exposes a `$sample` endpoint or one must be added;
  confirm the contract before wiring step 3.

## Remaining

All steps.
