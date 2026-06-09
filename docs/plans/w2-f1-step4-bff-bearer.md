# Plan — Complete W2-F1 step 4 (BFF-Bearer, drop gateway cookie fallback)

## Context

`docs/FEATURE_STATUS.md` lists **W2-F1 (Nginx routing & local TLS)** as 🟡 In Progress.
The only open item is **spec step 4**: *"Update frontend env vars to access the
gateway via `/api/v1` instead of cross-port requests, resolving local CORS."*

Current state (verified):
- Browser data calls already use **relative** `/api/v1/*` (`client.ts` empty base).
- Through nginx, `location /api/v1/` proxies those **directly to the gateway**,
  which authenticates via an **`auth_token` cookie fallback** in the gateway
  (the Next.js BFF is skipped for data calls).
- A dead `NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8000` (cross-port) env var
  lingers, read by nothing.

The reviewer flagged the cookie fallback as a **workaround, not the spec wiring**.
Chosen approach (user-confirmed): **route `/api/v1/*` through the Next BFF
(Bearer), and remove the gateway cookie fallback** — making the BFF the single
auth-injection point and the gateway **Bearer-only**. Browser then talks only
same-origin (nginx→frontend), eliminating cross-port/CORS entirely.

## Changes

### 1. `nginx/nginx.conf` — stop proxying `/api/v1` straight to the gateway
- **Delete** the `location /api/v1/ { … }` block (lines ~69–80). With it gone,
  `/api/v1/*` falls through to `location /` → `frontend:3000`, where the Next
  BFF route handles it. The `/api/v1/`→`/v1/` rewrite is no longer needed — the
  BFF builds `/v1/{path}` itself.
- **Update** the comment block (lines ~59–68) to describe the BFF-Bearer flow
  and drop the "gateway auth_token fallback" wording.

### 2. `services/api-gateway-service/src/middleware/auth.py` — Bearer-only
- Remove the `auth_token: Optional[str] = Cookie(None)` parameter (lines ~33–34).
- Remove the `elif auth_token:` fallback branch (lines ~51–52).
- Remove the `_AUTH_COOKIE = "auth_token"` constant (line ~19) and the now-unused
  `Cookie` import.
- Update the docstring (no cookie path) and the 401 detail string
  ("Missing credentials: …" → "Missing Authorization header").
- The Bearer path (lines ~42–50) and JWT verification (lines ~60–88) are
  independent of the cookie code — they stay intact.

### 3. `docker-compose.yml` — drop the dead cross-port env var
- Remove `NEXT_PUBLIC_API_GATEWAY_URL: http://localhost:8000` (line 209). This is
  the cross-port browser config the spec wants gone. Server-side
  `API_GATEWAY_URL: http://api-gateway:8000` (line 208) stays — the BFF uses it.

### 4. `frontend/Dockerfile` — remove unused build arg/env (cleanup)
- Remove `ARG`/`ENV NEXT_PUBLIC_API_GATEWAY_URL` (lines 47, 50). Read by no code.
  (`NEXT_PUBLIC_INTERVIEW_WS_URL` is also dead but out of scope — leave it.)

### 5. No change needed
- `frontend/src/lib/api/client.ts` — already builds relative `/api/v1/*`.
- `frontend/src/app/api/v1/[...path]/route.ts` — already lifts the cookie via
  `getSession()`, adds `Authorization: Bearer`, strips the prefix to `/v1/{path}`,
  and seeds `X-Correlation-Id`. This becomes the sole `/api/v1` path in the stack.
- `server.ts` and the `/api/auth/*`, `/api/dashboard/*` BFF routes — already
  Bearer / server-side; unaffected.

### 6. Gateway tests — `services/api-gateway-service/tests/test_routing.py`
- No existing test references the cookie path (verified), so the signature change
  won't break current tests. Add/keep cases asserting: valid `Bearer` → routes +
  `X-User-*` injected; **no** `Authorization` header → 401; public
  `/v1/api/auth/login|register` still pass through without auth.

### 7. Docs — flip W2-F1 to ✅
- `docs/FEATURE_STATUS.md`: W2-F1 row 🟡 → ✅; update "Last assessed".
- `docs/features/w2-f1-nginx-routing-tls.md`: re-check step 4 ✅ (env points at
  same-origin `/api/v1` via BFF, no cross-port), Remaining → None, note the
  gateway is now **Bearer-only** (cookie fallback removed) and the trace path is
  now nginx → frontend(BFF) → gateway.

## Risk / note to surface

Removing nginx's direct `/api/v1` route adds one hop to every browser data call
(browser → nginx → **frontend BFF** → gateway) and re-encodes responses via the
BFF's `NextResponse.json` (which yields `null` on empty/204 bodies). This is the
intended BFF pattern but is a latency + response-shape change vs. the current
direct-to-gateway path — verify DELETE/204 flows still behave.

## Version control

Work happens in the `rev-eval/` git repo (root is not a repo).

1. Branch off `richardh`: `git checkout richardh && git pull && git checkout -b richardh-feat-W2F1`.
2. Commit at major milestones (not one giant commit):
   - **Commit 1 — gateway Bearer-only:** auth.py cookie-fallback removal (change 2)
     + the gateway test cases (change 6).
   - **Commit 2 — edge wiring:** nginx.conf `/api/v1` route removal + comment
     (change 1), `docker-compose.yml` + `frontend/Dockerfile` env cleanup
     (changes 3–4).
   - **Commit 3 — docs:** flip W2-F1 to ✅ in `FEATURE_STATUS.md` + the detail
     file (change 7).
3. Commit messages end with the `Co-Authored-By: Claude` trailer. Do **not** push
   or open a PR unless asked — commits stay local on `richardh-feat-W2F1`.

## Verification

1. **Gateway unit tests:** `cd services/api-gateway-service && pytest -q` → green.
2. **Full stack:** `docker compose up --build`; log in via the UI (sets the
   `auth_token` cookie). Confirm a data call (e.g. trainer tests list) succeeds:
   browser `/api/v1/...` → nginx → frontend BFF → gateway, gateway logs show
   `X-User-*` injected (Bearer, not cookie).
3. **Negative (Bearer-only):**
   - `curl -k https://localhost/api/v1/api/tests` with no cookie/Bearer → 401
     ("Not authenticated" from the BFF).
   - Direct gateway with cookie only, no Bearer:
     `curl -H 'Cookie: auth_token=<jwt>' http://localhost:8000/v1/api/tests` → 401
     (fallback gone).
4. **Trace continuity:** in Grafana/Loki confirm one `correlation_id` spans
   nginx → frontend → gateway for a data call (W2-F3 unaffected).
5. **204 path:** exercise a DELETE through `/api/v1` and confirm no 500 / sane body.
