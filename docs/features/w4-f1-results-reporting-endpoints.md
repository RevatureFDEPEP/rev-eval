# W4-F1 — Candidate Results Reporting Endpoints (Filtering + Pagination)

**Status:** ✅ Completed
**Spec:** `days_16_20_features.md` §1 (Day 16)
**Depends on:** [W2-F7](w2-f7-alembic-category-domain.md) (reporting-and-analytics-service scaffold + Alembic env must exist before new reporting tables can be migrated — scaffold steps are in the W2-F7 detail file), [W3-F2](w3-f2-scoring-engine-locking.md) (sessions/answers tables must hold scored data for the aggregations to read)
**Unblocks:** [W4-F2](w4-f2-candidate-results-page.md) (results page fetches `GET /reports/user/{id}`), [W4-F3](w4-f3-rbac-aggregate-queries.md) (require_trainer gate + aggregate endpoints extend this scaffolding), [W4-F5](w4-f5-tech-debt-audit-adrs.md) (cross-service data-access decision is one required ADR)
**Last updated:** 2026-06-17

Build the read-heavy `GET` endpoints in reporting-and-analytics-service that
serve the candidate results page: a summary envelope, a paginated attempt
history, and per-entity aggregates.

## Steps

- [x] **1. Data-access decision + migration** — chose direct-read (shared DB):
      reporting service opens a second SQLAlchemy engine pointing to `eval_ai_dev`.
      ADR at `docs/adr/w4-f1-reporting-data-access.md`. Migration `0002_direct_read_adr`
      is a no-op (no new tables in `reporting_dev`). *(This ADR is one of the two required by W4-F5.)*
- [x] **2. GET /reports/user/{user_id}** — summary envelope: total attempts,
      avg score, best score, total time spent, most-recent attempt. Single
      aggregate query using `func.avg`/`func.count`/`func.max` + separate subquery for
      most-recent row. `total_time_spent_seconds` uses `func.extract("epoch", ...)`
      (PG-specific; isolated to its own query with try/except + negative-value clamp for SQLite).
      — `services/reporting-and-analytics-service/src/v1/routes/reports.py`
- [x] **3. GET /reports/user/{user_id}/attempts** — paginated history. Pydantic
      `@dataclass` dependency (`AttemptsFilter`): `page` (default 1), `size` (default 20,
      max 100), `test_id?`, `from?`/`to?` (date), `status?` (enum), `sort`
      (`field:direction`, default `submitted_at:desc`, allowed fields: `submitted_at`/`created_at`).
      Returns `{items, total, page, size}`.
      — `services/reporting-and-analytics-service/src/v1/routes/reports.py`
- [x] **4. CORS** — `CORSMiddleware` tightened from `"*"` to `http://localhost:3000`.
      — `services/reporting-and-analytics-service/main.py`
- [x] **5. Gateway routes** — added `"reporting-and-analytics-service": 8004` to
      `SERVICE_PORTS` and `^/v1/api/reports(/.*)?$` to `ROUTES`.
      — `services/api-gateway-service/main.py`
- [x] **6. Unit tests** — 15 pytest tests with SQLite in-memory fixture (`StaticPool`):
      pagination meta, filter by test_id/status/date range, sort, aggregate values,
      400 on invalid sort field, 422 on size > 100.
      — `services/reporting-and-analytics-service/tests/`

## Evidence

- Commit: `058d45c feat(w4-f1): reporting endpoints — GET /reports/user/{id} + paginated attempts`
- Branch: `tianyac-reporting-endpoints`
- Plan: `docs/plans/w4-f1-results-reporting-endpoints-plan.md`
- ADR: `docs/adr/w4-f1-reporting-data-access.md`

## Notes

- Hard prerequisite: `reporting-and-analytics-service` must be scaffolded
  (FastAPI layout, dedicated `reporting-postgres`, Alembic baseline) before
  these endpoints exist. Scaffold steps are tracked in
  [W2-F7](w2-f7-alembic-category-domain.md) under "Reporting Service Scaffold".
- The shared-DB-vs-HTTP decision drives whether reporting even needs its own
  tables; decided in step 1 (direct-read, no new tables).
- **Rolled in from W3-F6:** session finalize never writes `test_submissions`
  (the sessions/answers slice and the seeded submissions are parallel
  systems), so a just-taken quiz shows no score anywhere — the Playwright
  happy path had to drop its score-summary assertion (see
  [w3-f6 Notes](w3-f6-playwright-e2e-smoke.md)). Resolved: reporting service
  reads `quiz_sessions`/`session_answers` directly; W4-F2's results page
  will be the score summary the W3-F6 spec asked for.

## Remaining

Nothing — all steps complete.
