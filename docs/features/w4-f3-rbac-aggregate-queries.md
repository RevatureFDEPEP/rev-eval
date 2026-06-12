# W4-F3 — Role-Based Authorization (API Layer) + Aggregate Reporting Queries

**Status:** ✅ Completed
**Spec:** `days_16_20_features.md` §3 (Day 18)
**Depends on:** [W4-F1](w4-f1-results-reporting-endpoints.md) (the reporting service must have working endpoints to gate; aggregate endpoints extend the same scaffolding), [W3-F2](w3-f2-scoring-engine-locking.md) (answers/scoring data must be populated for `GROUP BY` + window-function queries to be meaningful)
**Unblocks:** [W4-F4](w4-f4-trainer-dashboard-frontend.md) (backend RBAC gate must exist before frontend enforcement is meaningful; the dashboard fetches these trainer-only endpoints)
**Branch:** `richardh-feat-W4F3` · **Plan:** [docs/plans/w4-f3-rbac-aggregate-queries.md](../plans/w4-f3-rbac-aggregate-queries.md)
**Last updated:** 2026-06-12

Add JWT-claim verification + a `require_trainer` dependency to the reporting
service, then implement the `GROUP BY` / `HAVING` / window-function queries that
power the trainer dashboard.

## Steps

- [x] **1. require_trainer dependency** — decode the `Authorization` JWT with
      python-jose + the shared `JWT_SECRET`; **401** on invalid signature /
      expired `exp`; **403** when the verified `role` claim ≠ `TRAINER`. Read
      role only from the verified payload, never the request body.
      *Evidence:* `services/reporting-and-analytics-service/src/v1/dependencies/auth.py`
      (commit `e6448f4`) — 401 on missing/non-Bearer header and any `JWTError`
      (bad signature, expired `exp`); 403 only for a *verified* non-TRAINER
      claim. `python-jose[cryptography]` added to requirements; `JWT_SECRET` /
      `JWT_ALGORITHM` in `src/config/settings.py` and the service's
      docker-compose env block (defaults match user-service's signing key).
- [x] **2. GET /reports/aggregate** (gated) — `GROUP BY test_id`: total
      attempts, distinct candidate count, avg score, pass rate (% above a
      configurable threshold), median time-to-complete via
      `percentile_cont` window function.
      *Evidence:* `ReportRepository.aggregate_by_test`
      (`src/repositories/report_repository.py`, commit `1b4bcbf`) — one
      GROUP BY statement over SUBMITTED sessions; pass rate against the
      `REPORT_PASS_THRESHOLD` setting (default 70.0, env-overridable);
      `percentile_cont(0.5) WITHIN GROUP` on Postgres with a portable
      ROW_NUMBER median for the sqlite test fixture (`_median_duration_parts`,
      integer-arithmetic fix in `af4f019`); optional `test_id`/`from`/`to`
      filters plus `min_attempts` rendered as a **HAVING** clause. Route gated
      with `Depends(require_trainer)` (`src/v1/routes/report_route.py`).
- [x] **3. GET /reports/test/{test_id}/questions** (gated) — per-question
      difficulty: correct-answer rate, hardest→easiest rank via `RANK() OVER
      (ORDER BY correct_rate ASC)`, score-distribution histogram buckets.
      *Evidence:* `ReportRepository.question_difficulty` (commit `673c108`) —
      GROUP BY the stable Mongo `question_id` (`question_index` varies per
      session under random sampling), `RANK() OVER (ORDER BY correct_rate
      ASC)` so rank 1 = hardest (ties share a rank), 4-bucket histogram over
      the [0, 1] partial-credit scores via portable `sum(case(...))`. 404 for
      an unknown test. `TmsAnswer` read-only mapping gained
      `question_id`/`is_correct` (mapping-only — TMS owns the schema, reporting
      Alembic stays at `0001`).
- [x] **4. Gateway awareness** — the `^/v1/api/reports` route from W4-F1 already
      forwards these; confirm the gateway injects `Authorization`/`X-User-*` so
      `require_trainer` can verify. (Gateway is the only auth boundary — but
      this gate is defense-in-depth, see step 5.)
      *Evidence:* gateway `ROUTES` pattern `^/v1/api/reports(/.*)?$`
      (`services/api-gateway-service/main.py:60`) matches both new paths — no
      ROUTES change needed; the proxy forwards the original headers downstream,
      stripping only host/content-length/x-forwarded-* (`main.py:212–228`), so
      the Bearer token arrives intact. Verified live through `:8000` (see
      smoke below). Gateway suite: 51 passed, unchanged.
- [x] **5. Unit tests + defense-in-depth** — pytest with a dependency override:
      no-dep → 403, candidate role → 403, verified trainer → 200 with expected
      shape. Exercise the gate via curl-equivalent requests that bypass all
      frontend guards, documenting the independent-enforcement posture.
      *Evidence:* commit `9294763` — `tests/test_auth_dependency.py` exercises
      the **real** gate with real HS256 tokens (missing/garbage/wrong-secret/
      expired → 401; PARTICIPANT and ADMIN → 403; TRAINER → 200; spoofed
      `X-User-Role: TRAINER` headers with no/participant token → 401/403; role
      in query string ignored). `tests/test_aggregate_endpoints.py` overrides
      `require_trainer` and asserts aggregate values, HAVING, filters, RANK tie
      ordering, histogram buckets, and the 404. Suite: **40 passed, 92.62%
      coverage** (was 20).

## Defense-in-depth posture

Platform-wide, the API gateway is the sole auth boundary and downstream
services trust its `X-User-*` headers. The reporting service's trainer
endpoints deliberately break that pattern — `require_trainer`
(`src/v1/dependencies/auth.py`) re-verifies the `Authorization` JWT with the
shared signing key and reads the role **only** from the verified payload. A
caller who bypasses the gateway entirely (curl straight to `:8004` with
spoofed `X-User-Role: TRAINER`) is rejected: 401 without a token, 403 with a
participant token. This is enforced independently of every frontend guard and
verified both in unit tests and against the live stack.

## Live smoke (2026-06-12, compose stack)

Through the gateway (`:8000`): trainer login → `GET /v1/api/reports/aggregate`
**200** with real Postgres `percentile_cont` output
(`{"test_id":1,…,"total_attempts":3,"distinct_candidates":2,"avg_score":12.22,"pass_rate":0.0,"median_duration_seconds":26.81}`,
`pass_threshold` 70.0); participant token → **403**; no token → **401**;
`/reports/test/1/questions` → **200** with ranks + histograms;
`/reports/test/999/questions` → **404**; `?min_attempts=5` → empty items
(HAVING); `?min_attempts=0` → **422**. Direct to `:8004` with spoofed
`X-User-Role: TRAINER`: **401** (no token) / **403** (participant token).

## Notes

- **Security note:** per [CLAUDE.md](../../CLAUDE.md), downstream services
  currently *trust* `X-User-*` and do not re-verify the JWT — the gateway is the
  sole auth boundary. This feature deliberately adds an **independent** JWT
  verification in the reporting service (defense-in-depth), the first service to
  do so. Keep `JWT_SECRET` shared with user-service's signing key.
- The scoring algorithm behind these aggregates is W3-F2's choice — its ADR is
  required by [W4-F5](w4-f5-tech-debt-audit-adrs.md).
- **Recorded deviations/decisions:** (1) the gate is spec-strict — only
  `TRAINER` passes; `ADMIN` gets 403 (widening is a one-line change if W4-F4
  needs it). (2) `percentile_cont` runs on the Postgres path; the sqlite unit
  fixture can't parse `WITHIN GROUP`, so it uses a portable ROW_NUMBER median
  (same dialect-branch precedent as W4-F1's `_duration_seconds`) — the live
  smoke covers the real `percentile_cont`. (3) W4-F1's per-user endpoints stay
  ungated (candidates read their own results); self-or-trainer authorization
  is noted for W4-F5's debt inventory.

## Remaining

None.
