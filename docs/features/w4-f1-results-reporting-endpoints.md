# W4-F1 — Candidate Results Reporting Endpoints (Filtering + Pagination)

**Status:** ✅ Completed
**Spec:** `days_16_20_features.md` §1 (Day 16)
**Depends on:** [W2-M10](w2-m10-reporting-service-scaffold.md) + [W2-F7](w2-f7-alembic-category-domain.md) (reporting-and-analytics-service must be scaffolded with a working Alembic env + Postgres before new reporting tables can be migrated), [W3-F2](w3-f2-scoring-engine-locking.md) (sessions/answers tables must hold scored data for the aggregations to read)
**Unblocks:** [W4-F2](w4-f2-candidate-results-page.md) (results page fetches `GET /reports/user/{id}`), [W4-F3](w4-f3-rbac-aggregate-queries.md) (require_trainer gate + aggregate endpoints extend this scaffolding), [W4-F5](w4-f5-tech-debt-audit-adrs.md) (cross-service data-access decision is one required ADR)
**Last updated:** 2026-06-12 (completed on branch `richardh-feat-W4F1`; plan: [w4-f1 plan](../plans/w4-f1-results-reporting-endpoints.md))

Build the read-heavy `GET` endpoints in reporting-and-analytics-service that
serve the candidate results page: a summary envelope, a paginated attempt
history, and per-entity aggregates.

## Steps

- [x] **1. Data-access decision + migration** — **direct read (shared-DB)**:
      a second read-only async engine in the reporting service pointed at
      test-management's `eval_ai_dev`, querying `sessions`/`answers`/`tests`
      via read-only mapped copies on a separate `TmsBase`
      (`src/models/tms_readonly.py`; engine + `get_tms_db` in
      `src/db/session.py`). Trade-offs vs HTTP-call and event-projection
      recorded in [ADR 0001](../adr/0001-reporting-cross-service-data-access.md).
      *Consequence: no reporting-side tables — Alembic `0001_baseline` remains
      head; the migration this step asks for is empty by decision, not
      omission (the ADR records this explicitly).* Compose grants `TMS_DB_*`
      env + a `postgres: service_healthy` dependency (`docker-compose.yml`).
- [x] **2. GET /reports/user/{user_id}** — summary envelope (total attempts,
      avg score, best score, total time spent, most-recent attempt) in one
      SQLAlchemy round trip: per-session score subquery
      (`AVG(answers.score)*100`), `func.count`/`func.avg`/`func.max`/`func.sum`
      aggregates over SUBMITTED sessions, LIMIT-1 subquery outer-joined for
      the most-recent row — no client-side re-aggregation
      (`src/repositories/report_repository.py:44`,
      `src/v1/routes/report_route.py:21`). Zero attempts → 200 zeroed
      envelope, not 404.
- [x] **3. GET /reports/user/{user_id}/attempts** — paginated history via the
      `AttemptsQuery` Pydantic dependency
      (`src/schemas/report_schema.py:56`): `page` (≥1, default 1), `size`
      (1–100, default 20), `test_id?`, `from?`/`to?` (dates, aliased — bound
      the attempt start time), `status?` (enum), `sort` =
      `field:direction` whitelisted to {submitted_at, created_at, score} ×
      {asc, desc}, default `submitted_at:desc` with NULLs last. Returns
      `{items, total, page, size}`; ACTIVE/EXPIRED rows expose `score: null`
      (`src/repositories/report_repository.py:100`,
      `src/v1/routes/report_route.py:32`).
- [x] **4. CORS** — already satisfied by the W2-M10 scaffold:
      `CORSMiddleware` reads `ALLOW_ORIGINS` (`main.py:14-27`), set to
      `http://localhost:3000` in compose (`docker-compose.yml` reporting
      service env). Verified, no change needed.
- [x] **5. Gateway routes** — `^/v1/api/reports(/.*)?$` →
      `reporting-and-analytics-service` + `SERVICE_PORTS` entry (8004) in
      `services/api-gateway-service/main.py:45,60`; routing test table
      extended (`services/api-gateway-service/tests/test_routing.py`).
- [x] **6. Unit tests** — `tests/test_report_endpoints.py` (17 tests) over an
      aiosqlite in-memory `TmsBase` fixture with `get_tms_db` overridden:
      aggregate values vs hand-computed, most-recent selection, zero-attempt
      envelope, user isolation, each filter, pagination meta, sort whitelist
      + 422s, ACTIVE `score: null`. Suite: 20 passed.

## Notes

- The shared-DB-vs-HTTP decision is recorded in
  [ADR 0001](../adr/0001-reporting-cross-service-data-access.md) — one of the
  two ADRs W4-F5 requires.
- **W3-F6 rolled-in item resolved:** scores become user-visible through these
  read endpoints (W4-F2's results page renders them) — finalize is *not*
  bridged into `test_submissions`, and no reporting-side mirror exists; the
  ADR names the alternatives and why they lost.
- Service-level authz is intentionally absent in W4-F1: the gateway JWT check
  is the boundary (as for every downstream service); `require_trainer` /
  self-access enforcement lands in [W4-F3](w4-f3-rbac-aggregate-queries.md).
- Live smoke (compose stack): login `student1@revature.com` → gateway
  `GET /v1/api/reports/user/3` returned the real W3-era attempt (33.33%,
  26.81s) with `most_recent` populated; `/attempts` listed the SUBMITTED row
  plus an ACTIVE row with `score: null`; `status=ACTIVE` filter, bad-sort
  422, missing-JWT 401, and direct `:8004` all behaved.

## Remaining

None.
