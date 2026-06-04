# F1 — Nginx Path-Based Routing & Local TLS

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §1 (Day 6) — priority REQUIRED
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton), W3-F6 (Playwright E2E), W4-F2 (Candidate Results Page), W4-F4 (Trainer Dashboard)
**Last updated:** 2026-06-04

Wire Nginx as the unified, secure entry point: TLS on :443, path-based routing
to the frontend and the API gateway.

## Steps

- [x] **1. Reverse proxy on :80 and :443** — `nginx/nginx.conf`: TLS
      termination on :443, :80 → :443 permanent redirect. Request-time DNS via
      Docker's embedded resolver (`127.0.0.11`) so nginx survives service
      restarts.
- [x] **2. Route configuration** — `/api/v1/*` → `api-gateway:8000` with
      `/api/v1/` → `/v1/` rewrite (gateway `ROUTES` matches `/v1/api/*`).
      Everything else — incl. `/`, `/_next/*`, and intentionally `/api/auth/*`
      (BFF must set the httpOnly `auth_token` cookie) — → frontend :3000.
      WebSocket upgrade map for Next.js HMR.
- [x] **3. Local certificates** — self-signed cert (CN=localhost, SAN
      localhost/127.0.0.1) generated with openssl, mounted from `nginx/certs/`
      (not committed; `localhost.crt` present locally).
- [x] **4. Frontend access via `/api/v1`** — browser data calls go through
      nginx → gateway; the gateway's `auth_token` cookie fallback handles auth,
      so the BFF is bypassed for data calls (login/register still via BFF).

## Beyond spec

- JSON access logs (`log_format json_combined`) to stdout, shipped to Loki by
  Promtail — feeds [F3](f3-log-aggregation.md).
- `X-Correlation-Id` pass-through with `$request_id` fallback for distributed
  log tracing.

## Remaining

None.
