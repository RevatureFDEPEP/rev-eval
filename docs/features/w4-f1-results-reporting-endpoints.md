# W4-F1 — Candidate Results Reporting Endpoints (Filtering + Pagination)

**Status:** ❌ Not Started
**Spec:** `days_16_20_features.md` §1 (Day 16)
**Depends on:** [W2-F7](w2-f7-alembic-category-domain.md) (reporting-and-analytics-service scaffold + Alembic env must exist before new reporting tables can be migrated — scaffold steps are in the W2-F7 detail file), [W3-F2](w3-f2-scoring-engine-locking.md) (sessions/answers tables must hold scored data for the aggregations to read)
**Unblocks:** [W4-F2](w4-f2-candidate-results-page.md) (results page fetches `GET /reports/user/{id}`), [W4-F3](w4-f3-rbac-aggregate-queries.md) (require_trainer gate + aggregate endpoints extend this scaffolding), [W4-F5](w4-f5-tech-debt-audit-adrs.md) (cross-service data-access decision is one required ADR)
**Last updated:** 2026-06-08

Build the read-heavy `GET` endpoints in reporting-and-analytics-service that
serve the candidate results page: a summary envelope, a paginated attempt
history, and per-entity aggregates.

## Steps

- [ ] **1. Data-access decision + migration** — choose direct-read (shared DB)
      vs. HTTP-call vs. event-projection / sessions-mirror table; record the
      trade-offs in an ADR (`docs/adr/`). Generate the Alembic migration for any
      reporting-side tables. *(This ADR is one of the two required by W4-F5.)*
- [ ] **2. GET /reports/user/{user_id}** — summary envelope: total attempts,
      avg score, best score, total time spent, most-recent attempt. Single
      SQLAlchemy query using `func.avg`/`func.count`/`func.sum` + a subquery for
      the most-recent row (no client-side re-aggregation).
- [ ] **3. GET /reports/user/{user_id}/attempts** — paginated history. Query
      params via a Pydantic dependency: `page` (default 1), `size` (default 20,
      max 100), `test_id?`, `from?`/`to?` (date), `status?` (enum), `sort`
      (`field:direction`, default `submitted_at:desc`). Return `{items, total,
      page, size}`.
- [ ] **4. CORS** — `CORSMiddleware` allowing the frontend origin
      (`http://localhost:3000`).
- [ ] **5. Gateway routes** — add `^/v1/api/reports(/.*)?$` → reporting service
      in `services/api-gateway-service/main.py`.
- [ ] **6. Unit tests** — pytest with a test-DB fixture: assert pagination
      meta, filter application, and aggregate values from a seeded dataset.
      Evidence: `services/reporting-and-analytics-service/tests/`.

## Notes

- Hard prerequisite: `reporting-and-analytics-service` must be scaffolded
  (FastAPI layout, dedicated `reporting-postgres`, Alembic baseline) before
  these endpoints exist. Scaffold steps are tracked in
  [W2-F7](w2-f7-alembic-category-domain.md) under "Reporting Service Scaffold".
- The shared-DB-vs-HTTP decision drives whether reporting even needs its own
  tables; make it in step 1 before writing queries.
- **Rolled in from W3-F6:** session finalize never writes `test_submissions`
  (the sessions/answers slice and the seeded submissions are parallel
  systems), so a just-taken quiz shows no score anywhere — the Playwright
  happy path had to drop its score-summary assertion (see
  [w3-f6 Notes](w3-f6-playwright-e2e-smoke.md)). The step-1 ADR should settle
  how scores become user-visible (read `sessions`/`answers` directly vs.
  bridge finalize → `test_submissions` vs. a reporting-side mirror); W4-F2's
  results page is then the score summary the W3-F6 spec asked for.

## Remaining

All steps.
