# W4 Reporting Slice — User Acceptance Tests (W4-F1 + W4-F2)

_Drafted 2026-06-17. Covers W4-F1 (Candidate Results Reporting Endpoints) and
W4-F2 (Candidate Results Page). Steps are grounded in a live run against the
local Docker stack. Local-only doc._

## Scope

- **W4-F1** — `reporting-and-analytics-service` read-only endpoints:
  `GET /reports/user/{id}` (summary) and `GET /reports/user/{id}/attempts`
  (paginated history), behind the gateway's header-trust authorization.
- **W4-F2** — `/results/[sessionId]` Next.js page that consumes W4-F1: streamed
  summary + attempts table + score chart, with loading, error, not-found, and
  auth states.

## Environment & preconditions

1. **Stack up and healthy.** From the repo root:
   ```bash
   docker compose up -d --build      # first time / after pulling F1
   docker compose ps                 # all 10 services "healthy"
   ```
   Confirm the new service and route:
   ```bash
   curl -s http://localhost:8004/health                 # {"status":"ok"}
   curl -s http://localhost:8000/routes | grep reports  # reports route present
   ```
2. **A participant account exists.** If the DB is empty, register one (public route):
   ```bash
   curl -s -X POST http://localhost:8000/v1/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"rev-eval.test002@yopmail.com","password":"password123","first_name":"Test","last_name":"Two","role":"PARTICIPANT"}'
   ```
   Note the returned `user.id` (call it **PID**; it was `1` in the reference run).
3. **A trainer account** (for the cross-user authorization test):
   ```bash
   curl -s -X POST http://localhost:8000/v1/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"rev-eval.test001@yopmail.com","password":"password123","first_name":"Test","last_name":"One","role":"TRAINER"}'
   ```
4. **At least one SUBMITTED attempt for the participant.** Quiz sessions are
   created at runtime, not seeded, so either complete a quiz through the UI/API,
   OR seed one deterministically (score = 1/2 = 50%, 300s elapsed) for a
   repeatable UAT:
   ```bash
   docker compose exec -T postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
   INSERT INTO tests (id, name, test_type) VALUES (1, 'Python Basics Quiz', 'QUIZ') ON CONFLICT (id) DO NOTHING;
   INSERT INTO quiz_sessions (session_id, test_id, user_id, session_token, status, question_ids, current_index, created_at, started_at, expires_at, submitted_at, updated_at, draft_version)
   VALUES ('11111111-1111-1111-1111-111111111111', 1, 1, 'uat-token-1', 'SUBMITTED', '["q1","q2"]', 2,
           now() - interval '5 minutes', now() - interval '5 minutes', now() + interval '1 hour', now(), now(), 0);
   INSERT INTO session_answers (session_id, question_id, question_index, submitted_answers, is_correct, points_earned, max_points, requires_manual_review, idempotency_key, created_at)
   VALUES ('11111111-1111-1111-1111-111111111111','q1',0,'[1]', true, 1.0, 1.0, false, 'uat-1-0', now()),
          ('11111111-1111-1111-1111-111111111111','q2',1,'[2]', false, 0.0, 1.0, false, 'uat-1-1', now());
   SQL
   ```
   (Replace `user_id`/`test_id` if PID ≠ 1. The featured session id is
   `11111111-1111-1111-1111-111111111111` = **SID**.)
5. **Get a participant token** for API tests:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/v1/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"rev-eval.test002@yopmail.com","password":"password123"}' \
     | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
   ```

---

## Section A — W4-F1 Reporting Endpoints (API)

| ID | Objective | Steps | Expected result | P/F |
|----|-----------|-------|-----------------|-----|
| **A1** | Summary returns correct aggregates | `curl -s http://localhost:8000/v1/api/reports/user/$PID -H "Authorization: Bearer $TOKEN"` | HTTP 200. `total_attempts=1`, `average_score=0.5`, `best_score=0.5`, `total_time_spent_seconds=300`, `most_recent_attempt.test_name="Python Basics Quiz"`, `.score=0.5`, `.correct_count=1`, `.total_answered=2`, `.status="SUBMITTED"`. | |
| **A2** | Attempts history shape | `curl -s "http://localhost:8000/v1/api/reports/user/$PID/attempts?page=1&size=100" -H "Authorization: Bearer $TOKEN"` | HTTP 200. `{items:[1 row], total:1, page:1, size:100}`; the row matches A1's attempt. | |
| **A3** | Pagination metadata | Append `?page=1&size=1`; then `?page=2&size=1` | Page 1 → 1 item, `size:1`; page 2 → `items:[]` (only one attempt exists). `total` stable at 1. | |
| **A4** | Status filter | `...attempts?status=ACTIVE` then `?status=SUBMITTED` | `ACTIVE` → empty; `SUBMITTED` → the seeded row. | |
| **A5** | test_id filter | `...attempts?test_id=1` then `?test_id=999` | `test_id=1` → the row; `test_id=999` → empty. | |
| **A6** | Date range filter | `...attempts?from=2020-01-01&to=2020-01-02` then today's range | Out-of-range → empty; range covering today → the row. | |
| **A7** | Sort validation | `...attempts?sort=submitted_at:asc` (valid) then `?sort=score:desc` (invalid field) | Valid → 200. Invalid field → **422** with detail naming the sortable fields. | |
| **A8** | Empty candidate | Use a freshly-registered participant's id + their token | HTTP 200, `total_attempts:0`, all scores `null`, `most_recent_attempt:null`; attempts `{items:[],total:0,...}`. | |
| **A9** | Self-access only (authz) | As participant, `curl .../reports/user/<OTHER_ID> -H "Authorization: Bearer $TOKEN"` | **403** `Not authorized to view this user's reports`. | |
| **A10** | Trainer reads anyone | Log in as the trainer, request the participant's report with the trainer token | **200** with the participant's data (trainer override). | |
| **A11** | No gateway headers (defense) | Hit the reporting service directly bypassing the gateway: `curl -s http://localhost:8004/reports/user/$PID` (no X-User-* headers) | **403** (no identity headers ⇒ denied). | |
| **A12** | Routes through nginx | `curl -sk https://localhost/api/v1/reports/user/$PID -H "Authorization: Bearer $TOKEN"` | Same 200 envelope as A1 (full nginx → gateway → reporting path). | |

---

## Section B — W4-F2 Candidate Results Page (UI)

Sign in to the app at `https://localhost/` (accept the self-signed cert) as the
participant so the `auth_token` httpOnly cookie is set. Then exercise the page.

| ID | Objective | Steps | Expected result | P/F |
|----|-----------|-------|-----------------|-----|
| **B1** | Page renders three regions | Navigate to `https://localhost/results/<SID>` | Headline "Results", a summary region (Best/Average/Total attempts/Time spent cards), an "Attempt history" table, and a "Score trend" chart all render. | |
| **B2** | Summary values correct | Inspect the summary cards | Best score **50%**, Average **50%**, Total attempts **1**, Time spent **5m 0s**; "Most recent: Python Basics Quiz — 50% in 5m 0s (…)". | |
| **B3** | Attempt table row | Inspect the table | One row: test "Python Basics Quiz", status badge **SUBMITTED**, Score **50%**, Correct **1/2**, Time **5m 0s**, a submitted timestamp. | |
| **B4** | Featured attempt highlighted | Note the row matching `<SID>` | That row is visually highlighted and marked `aria-current="true"` (inspect DOM). | |
| **B5** | Chart renders accessibly | Inspect the "Score trend" chart | A bar chart with one bar at 50%; the featured bar is accented; the chart container exposes `role="img"` with an `aria-label` describing it. | |
| **B6** | Responsive layout | Resize to mobile width (≤640px) then desktop (≥1024px) | Mobile: single column. Desktop: summary cards in a row, table + chart side-by-side. No horizontal overflow (table scrolls within its panel). | |
| **B7** | Loading state | Throttle network (DevTools "Slow 3G") and reload `/results/<SID>` | A skeleton matching the layout appears first (route `loading.tsx` + per-region Suspense), replaced by content as each region streams. | |
| **B8** | Not-found state | Navigate to `https://localhost/results/not-a-real-session` | "Results not found" page with a "Back to dashboard" link (HTTP 200, not a crash). | |
| **B9** | Unauthenticated redirect | Sign out (or clear the `auth_token` cookie) and open `/results/<SID>` | Redirected to `/` (307). No results leaked. | |
| **B10** | Per-region error isolation | Stop the reporting service (`docker compose stop reporting-and-analytics-service`), reload `/results/<SID>` | The page chrome and summary heading still render; the affected region(s) show a red "We couldn't load … The rest of the page is unaffected." panel with a "Try again" button — the whole page does **not** blank. Restart the service and click "Try again" → the panel recovers. | |
| **B11** | Empty-history candidate | As a freshly-registered participant with no attempts, open `/results/<any-sid>` | "Results not found" (a candidate with zero attempts has no featured session). The summary/empty states are reachable only once they have ≥1 attempt. | |
| **B12** | No cross-user access | While signed in as the participant, there is no UI path or URL param that fetches another user's report (identity comes from the session, not the URL). Confirm changing the `[sessionId]` segment never surfaces another user's data. | Only the signed-in user's own attempts are ever shown; unknown ids → not-found. | |

---

## Section C — Failure-path & concurrency injection (executed 2026-06-17)

Run against the live stack to prove the shared-DB read-only design degrades
safely. All passed.

### C.1 Input / boundary / auth (endpoint hardening)

| ID | Injection | Result |
|----|-----------|--------|
| FP1 | non-integer `user_id` (`/user/abc`) | **422** |
| FP2 | `page=0` / `size=1000` / `size=-5` | **422** (ge=1, le=100) |
| FP3 | invalid `sort=score:desc`, garbage `sort=DROP TABLE` | **422** (field allow-list) |
| FP4 | invalid `status=HACKED`, SQLi `test_id=1;DROP+TABLE`, `from=not-a-date` | **422** (type/enum coercion — no SQLi reaches the DB) |
| FP5 | no token / garbage token | **401** (gateway) |
| FP6 | participant reads another user's report (IDOR), negative `user_id` | **403** (authz denies before any query) |

### C.2 Service-down (reporting unreachable)

- Endpoint through gateway while reporting stopped → **503 in ~0.07s** (fast
  fail, no hang).
- `/results/[sessionId]` page → **HTTP 200**, chrome + heading still render, **no
  whole-page 500**; the streamed RSC payload carries the `ServerApiError`/digest
  so the client renders the per-region "Try again" panel after hydration (the
  red panel is client-rendered — verify in a browser, not raw curl).
- Restart reporting → endpoint recovers to **200**.

### C.3 Concurrent shared reads

- 100 concurrent summary reads, 100 concurrent attempts reads, 200 reads @
  100-way parallelism → **100% HTTP 200**, deterministic body sizes, p50 ~340ms
  (~760ms at 100-way). No connection-pool exhaustion, no 5xx.

### C.4 Reads during concurrent writes (the ADR-0001 case)

- A background loop toggled a 2nd SUBMITTED session (flipping `total_attempts`
  1↔2) while 520 reads hammered the summary endpoint → **520/520 HTTP 200**, no
  torn/errored reads.
- Snapshots observed: `(1, 0.5, 0.5)` and `(2, 1.0, 0.75)` (both fully coherent),
  plus a brief `(2, 0.5, 0.5)`. The last is **not** corruption: the summary is a
  **single rollup query (one MVCC snapshot)**, and F1's contract counts all
  attempts but scores only answered SUBMITTED ones — so a session row visible
  before its answers (or a real in-progress ACTIVE attempt) correctly shows in
  `total_attempts` without yet contributing a score. It self-heals once answers
  commit; production scoring commits session+answers atomically (W3-F2).

**Conclusion:** read-only shared-DB access is safe under concurrency — Postgres
MVCC gives each read a consistent snapshot, readers never block writers, the
single-query summary is internally consistent, and every failure mode degrades
to a clean 4xx/5xx or an isolated UI panel rather than corruption or a hang.

## Exit criteria

- All Section A rows pass (endpoint correctness, filters, pagination, sort
  validation, and authorization — self/trainer/other/no-headers).
- All Section B rows pass (three-region render with correct values, featured
  highlight, accessibility, responsive layout, and full state coverage:
  loading / error-isolation / not-found / unauthenticated).
- Reference run (2026-06-17) confirmed A1, A2, A9, A12 and B1, B2, B3, B5, B8,
  B9 against the live stack; the remainder are scripted above for a full pass.
