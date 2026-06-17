# W2-F1 — Nginx Path-Based Routing & Local TLS

**Status:** ✅ Done
**Spec:** `days_6_10_features.md` §1 (Day 6) — priority REQUIRED
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton), W3-F6 (Playwright E2E), W4-F2 (Candidate Results Page), W4-F4 (Trainer Dashboard)
**Last updated:** 2026-06-13

Wire Nginx as the unified, secure entry point: TLS on :443, path-based routing
to the frontend and the API gateway.

## Steps

- [x] **1. Reverse proxy on :80 and :443** — `nginx/nginx.conf`: TLS
      termination on :443, :80 → :443 permanent redirect. Commits: `9dbcc51`
      (add TLS support), `3ae2443` (configure routes), `4625fe7` (complete
      routing todos).
- [x] **2. Basic route configuration** — `/_next/*` → `frontend:3000` with
      WebSocket upgrade for Next.js HMR; `/` → `frontend:3000`. `/api/v1/`
      currently routes **directly** to `api-gateway:8000` — the BFF bearer
      pattern (step 4) is not yet applied.
- [x] **3. Local certificates** — self-signed cert (CN=localhost) mounted at
      `/etc/nginx/ssl/cert.pem` (not committed; generated locally with openssl).
- [x] **4. BFF bearer pattern** — remove `location /api/v1/` direct-gateway
      block; route all `/api/v1/*` through `frontend:3000` so the Next.js BFF
      (`frontend/src/app/api/v1/[...path]/route.ts`) injects the `Bearer`
      header lifted from the httpOnly `auth_token` cookie. The BFF handler
      exists in code but nginx currently bypasses it.

## Evidence

- Branch `tianyac-feat-nginx` (merged into `tianyac`).
- Commits: `4625fe7`, `9dbcc51`, `3ae2443`.
- `nginx/nginx.conf`: active TLS on :443, :80 → :443 redirect, `/_next/`
  WebSocket upgrade, `/api/v1/` → `frontend:3000` BFF bearer pattern,
  JSON access logs, X-Correlation-Id pass-through, `resolver 127.0.0.11`.
