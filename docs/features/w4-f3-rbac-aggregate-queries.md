# W4-F3 — Role-Based Authorization (API Layer) + Aggregate Reporting Queries

**Status:** ❌ Not Started
**Spec:** `days_16_20_features.md` §3 (Day 18)
**Depends on:** [W4-F1](w4-f1-results-reporting-endpoints.md) (the reporting service must have working endpoints to gate; aggregate endpoints extend the same scaffolding), [W3-F2](w3-f2-scoring-engine-locking.md) (answers/scoring data must be populated for `GROUP BY` + window-function queries to be meaningful)
**Unblocks:** [W4-F4](w4-f4-trainer-dashboard-frontend.md) (backend RBAC gate must exist before frontend enforcement is meaningful; the dashboard fetches these trainer-only endpoints)
**Last updated:** 2026-06-08

Add JWT-claim verification + a `require_trainer` dependency to the reporting
service, then implement the `GROUP BY` / `HAVING` / window-function queries that
power the trainer dashboard.

## Steps

- [ ] **1. require_trainer dependency** — decode the `Authorization` JWT with
      python-jose + the shared `JWT_SECRET`; **401** on invalid signature /
      expired `exp`; **403** when the verified `role` claim ≠ `TRAINER`. Read
      role only from the verified payload, never the request body.
- [ ] **2. GET /reports/aggregate** (gated) — `GROUP BY test_id`: total
      attempts, distinct candidate count, avg score, pass rate (% above a
      configurable threshold), median time-to-complete via
      `percentile_cont` window function.
- [ ] **3. GET /reports/test/{test_id}/questions** (gated) — per-question
      difficulty: correct-answer rate, hardest→easiest rank via `RANK() OVER
      (ORDER BY correct_rate ASC)`, score-distribution histogram buckets.
- [ ] **4. Gateway awareness** — the `^/v1/api/reports` route from W4-F1 already
      forwards these; confirm the gateway injects `Authorization`/`X-User-*` so
      `require_trainer` can verify. (Gateway is the only auth boundary — but
      this gate is defense-in-depth, see step 5.)
- [ ] **5. Unit tests + defense-in-depth** — pytest with a dependency override:
      no-dep → 403, candidate role → 403, verified trainer → 200 with expected
      shape. Exercise the gate via curl-equivalent requests that bypass all
      frontend guards, documenting the independent-enforcement posture.

## Notes

- **Security note:** per [CLAUDE.md](../../CLAUDE.md), downstream services
  currently *trust* `X-User-*` and do not re-verify the JWT — the gateway is the
  sole auth boundary. This feature deliberately adds an **independent** JWT
  verification in the reporting service (defense-in-depth), the first service to
  do so. Keep `JWT_SECRET` shared with user-service's signing key.
- The scoring algorithm behind these aggregates is W3-F2's choice — its ADR is
  required by [W4-F5](w4-f5-tech-debt-audit-adrs.md).

## Remaining

All steps.
