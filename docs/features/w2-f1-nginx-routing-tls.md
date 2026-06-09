# W2-F1 — Nginx Path-Based Routing & Local TLS

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §1 (Day 6) — priority REQUIRED
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton), W3-F6 (Playwright E2E), W4-F2 (Candidate Results Page), W4-F4 (Trainer Dashboard)
**Last updated:** 2026-06-09

Wire Nginx as the unified, secure entry point: TLS on :443, path-based routing
to the frontend and the API gateway.

## Steps

- [x] **1. Reverse proxy on :80 and :443** — `nginx/nginx.conf`: TLS
      termination on :443, :80 → :443 permanent redirect. Request-time DNS via
      Docker's embedded resolver (`127.0.0.11`) so nginx survives service
      restarts.
- [x] **2. Route configuration** — **all** traffic → frontend :3000 (incl. `/`,
      `/_next/*`, and every `/api/*`). Data calls hit `/api/v1/*`, which the
      Next.js BFF (`frontend/src/app/api/v1/[...path]`) proxies to
      `api-gateway:8000` as `/v1/{path}` with a `Bearer` header. No direct
      nginx→gateway route — the BFF is the single auth-injection point.
      `/api/auth/*` likewise hits the BFF so it can set the httpOnly
      `auth_token` cookie. WebSocket upgrade map for Next.js HMR.
- [x] **3. Local certificates** — self-signed cert (CN=localhost, SAN
      localhost/127.0.0.1) generated with openssl, mounted from `nginx/certs/`
      (not committed; `localhost.crt` present locally).
- [x] **4. Frontend access via `/api/v1`** — done. The browser uses relative
      same-origin `/api/v1/*` (`client.ts`, empty base); these route through the
      Next.js BFF → gateway, no cross-port requests, no CORS. The dead
      cross-port `NEXT_PUBLIC_API_GATEWAY_URL` env was removed (compose +
      `frontend/Dockerfile`). The earlier gateway `auth_token` cookie fallback
      was **removed** — the gateway is now **Bearer-only** (the BFF lifts the
      cookie into the `Bearer` header), making the BFF the single auth boundary.

## Beyond spec

- JSON access logs (`log_format json_combined`) to stdout, shipped to Loki by
  Promtail — feeds [W2-F3](w2-f3-log-aggregation.md).
- `X-Correlation-Id` pass-through with `$request_id` fallback for distributed
  log tracing.

## Verification (full stack, 2026-06-09)

- Gateway Bearer-only: `Bearer` → 200; no header → 401; **cookie-only → 401**
  (fallback gone).
- Full path login + data call: BFF login (httpOnly cookie set) → `GET
  /api/v1/api/tests` through nginx → BFF → gateway → 200; gateway log shows
  `👤 User: trainer1@revature.com (TRAINER)` (Bearer-derived `X-User-*`).
- 204 path: routing `/api/v1` through the BFF exposed a latent BFF bug —
  `NextResponse.json(null, {204})` made a successful DELETE (gateway 204)
  surface as 500. **Fixed** (`api/v1/[...path]/route.ts` now passes bodyless
  204/205 through); re-verified unlink → 204.

## Remaining

None. Trace path is now nginx → frontend (BFF) → gateway for data calls; the
gateway is Bearer-only (cookie fallback removed on `richardh-feat-W2F1`).
