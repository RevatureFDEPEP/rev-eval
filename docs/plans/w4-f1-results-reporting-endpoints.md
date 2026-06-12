# Plan — W4-F1: Candidate Results Reporting Endpoints (Filtering + Pagination)

**Feature:** [W4-F1](../features/w4-f1-results-reporting-endpoints.md) · Spec: `days_16_20_features.md` §1 (Day 16)
**Depends on:** W2-M10 ✅ (reporting scaffold + Alembic), W2-F7 ✅, W3-F2 ✅ (scored `sessions`/`answers` data)
**Unblocks:** W4-F2 (results page), W4-F3 (require_trainer + aggregates), W4-F5 (this ADR is one of the two required)
**Branch:** `richardh-feat-W4F1` off `richardh`

## Locked decisions

1. **Data access = direct read (shared-DB pattern).** The reporting service gets a
   second, read-only async engine pointed at test-management-service's Postgres
   (`eval_ai_dev`) and queries `sessions` / `answers` / `tests` directly.
   - *Why not HTTP:* test-management-service has no bulk read endpoints; aggregation
     would move into app code, and W4-F3's GROUP BY / HAVING / window-function
     queries over the full sessions+answers tables are impractical over HTTP.
   - *Why not event projection / mirror table:* no message bus exists; a mirror adds
     sync lag + dual-write complexity for zero Day-16 benefit.
   - *Trade-off accepted:* schema coupling to tables owned by the TMS Alembic chain.
     Mitigated by confining the coupling to one module of read-only mapped models
     (`src/models/tms_readonly.py`, its own `TmsBase`) excluded from reporting's
     Alembic autogenerate, plus unit tests that pin the column contract.
   - **Consequence: no reporting-side tables.** Alembic `0001_baseline` stays the
     head; the ADR records that the migration required by spec step 1 is empty by
     decision, not omission.
2. **Attempt = a row in `sessions`.** Per-attempt score is derived in SQL as
   `AVG(answers.score) * 100` per session (answer scores are [0,1]; SUBMITTED
   sessions have every slot answered, so AVG ≡ sum/num_questions). ACTIVE/EXPIRED
   sessions get `score = NULL` in the attempts list and are excluded from summary
   aggregates.
3. **Summary aggregates run over SUBMITTED sessions only**; time spent =
   `submitted_at − server_now` (the server-anchored start), summed.
4. **No service-level authz in W4-F1.** The gateway JWT check is the boundary
   (as for every other service); `require_trainer` / self-access enforcement is
   W4-F3 by spec. Noted in the ADR + detail doc.

## Context

- `reporting-and-analytics-service` is scaffolded (W2-M10): FastAPI layout, CORS
  middleware already reading `ALLOW_ORIGINS` (`main.py:14-27`), own
  `reporting-postgres` (`eval_ai_reporting`), Alembic with empty `0001`,
  `start.sh` runs `alembic upgrade head`, `tests/` + `conftest.py` exist
  (hermetic env defaults), and the Dockerfile test stage runs `pytest -q`.
- Source data (TMS, `eval_ai_dev`): `sessions` (Alembic 0004–0007:
  `session_id UUID PK`, `test_id FK`, `user_id`, `status ACTIVE|SUBMITTED|EXPIRED`,
  `server_now`, `expires_at`, `submitted_at`, `question_ids JSON`, …) and
  `answers` (0005: `session_id FK`, `question_index`, `score FLOAT [0,1]`,
  `is_correct`, unique `(session_id, question_index)`). Finalize sets only
  `sessions.submitted_at`; **nothing writes `test_submissions`** — that parallel
  system is out of scope here (the ADR documents it; W4-F2 renders scores from
  these endpoints).
- Gateway `ROUTES` / `SERVICE_PORTS` have no reporting entries yet
  (`services/api-gateway-service/main.py:41-59`).
- CI already runs reporting tests (its `tests/` dir exists) — no workflow change.

## Step 0 — Branch & commit workflow

- `git fetch origin`; branch **`richardh-feat-W4F1`** created **off
  `origin/richardh`** (work happens in the `w3-remediation` worktree, where
  `richardh` itself is checked out elsewhere — use
  `git switch -c richardh-feat-W4F1 origin/richardh`).
- **First commit on the branch = this plan file.**
- One commit per milestone below, Conventional Commits (`feat(w4-f1): …`).

## Milestones

### M1 — ADR: cross-service data access
- `docs/adr/0001-reporting-cross-service-data-access.md` — context, decision
  (direct read), consequences, alternatives considered (HTTP call, event
  projection / sessions-mirror), the empty-migration consequence, and the
  score-visibility resolution rolled in from W3-F6 (scores become user-visible
  via these read endpoints + W4-F2, not by bridging finalize →
  `test_submissions`).
- Commit: `docs(w4-f1): ADR 0001 — reporting reads TMS Postgres directly`.

### M2 — Second engine + read-only TMS models + compose wiring
- `src/config/settings.py`: add `TMS_DB_HOST/PORT/USERNAME/PASSWORD/NAME` +
  `TMS_SQLALCHEMY_DATABASE_URL` property (defaults mirror TMS compose env:
  `postgres` / `5432` / `root` / `root` / `eval_ai_dev`).
- `src/db/session.py`: `tms_engine` + `TmsSessionLocal` + `get_tms_db()`
  dependency alongside the existing reporting engine. Reporting engine stays for
  future reporting-owned tables.
- `src/models/tms_readonly.py`: `TmsBase` + minimal mapped copies of
  `sessions`, `answers`, `tests` (only columns the queries need; portable
  `sa.Uuid` for `session_id` so the sqlite test fixture works). Module docstring:
  read-only, schema owned by TMS Alembic, do not autogenerate from this Base.
- `docker-compose.yml`: reporting service gains `TMS_DB_*` env +
  `depends_on: postgres: condition: service_healthy`.
- `conftest.py`: add `TMS_DB_*` hermetic defaults.
- Commit: `feat(w4-f1): read-only TMS engine + session/answer/test models`.

### M3 — GET /reports/user/{user_id} (summary envelope)
- `src/schemas/report_schema.py`: `MostRecentAttempt`, `UserSummary`
  (`user_id`, `total_attempts`, `avg_score`, `best_score`,
  `total_time_seconds`, `most_recent`).
- `src/repositories/report_repository.py`: single round-trip summary query —
  per-session score subquery (`AVG(answers.score)*100 GROUP BY session_id`)
  joined to SUBMITTED `sessions`, aggregated with `func.count` / `func.avg` /
  `func.sum(submitted_at − server_now)` / `func.max`, + ordered subquery for the
  most-recent attempt row. No Python-side re-aggregation.
- `src/services/report_service.py` + `src/v1/routes/report_route.py`
  (`router = APIRouter(prefix="/reports", …)`); include in `main.py` under
  `/v1/api`. Zero attempts → 200 with zeroed envelope / `most_recent: null`
  (not 404).
- Commit: `feat(w4-f1): user results summary endpoint with SQL aggregates`.

### M4 — GET /reports/user/{user_id}/attempts (filter + pagination)
- `AttemptsQuery` Pydantic dependency: `page≥1` (default 1), `1≤size≤100`
  (default 20), `test_id?`, `from?`/`to?` (dates, aliased — `from` is reserved),
  `status?` (ACTIVE|SUBMITTED|EXPIRED), `sort` = `field:direction` validated
  against whitelist {`submitted_at`,`created_at`,`score`} × {`asc`,`desc`},
  default `submitted_at:desc`, NULLs last.
- Repository: sessions LEFT JOIN per-session score subquery + `tests` (name),
  filters applied in SQL, `func.count` total + paginated items in the envelope
  `{items, total, page, size}`.
- Item shape: `session_id`, `test_id`, `test_name`, `status`, `started_at`
  (=`server_now`), `submitted_at`, `duration_seconds`, `score`.
- Commit: `feat(w4-f1): paginated attempt history with filters and sort`.

### M5 — Gateway route + CORS evidence
- `services/api-gateway-service/main.py`: `SERVICE_PORTS["reporting-and-analytics-service"] = 8004`;
  `ROUTES += {"pattern": r"^/v1/api/reports(/.*)?$", "service": "reporting-and-analytics-service"}`.
- CORS (spec step 4) is already satisfied by the W2-M10 scaffold
  (`main.py:14-27`, `ALLOW_ORIGINS`); verify `http://localhost:3000` allowed and
  cite as evidence rather than re-implementing.
- Commit: `feat(w4-f1): route /v1/api/reports through the gateway`.

### M6 — Unit tests
- `tests/test_report_endpoints.py` (+ fixture in `tests/conftest.py`): aiosqlite
  in-memory engine creating `TmsBase` tables, seeded dataset (multiple users,
  tests, SUBMITTED + ACTIVE + EXPIRED sessions, answers with known scores),
  app exercised via `httpx.ASGITransport` with `get_tms_db` dependency override.
- Assertions: aggregate correctness (count/avg/best/total-time vs hand-computed),
  most-recent selection, zero-attempt envelope, pagination meta (`total`, `page`,
  `size`, slicing), each filter (`test_id`, `from`/`to`, `status`), sort
  whitelist + 422 on bad `sort`/`size>100`, ACTIVE session `score: null`.
- `requirements-dev.txt`: add `aiosqlite` (mirrors TMS pin).
- Commit: `test(w4-f1): report endpoint suite over seeded sqlite fixture`.

## Testing & validation

| Check | Command (from) | Pass bar |
|---|---|---|
| Reporting unit tests | `pytest -q` (`services/reporting-and-analytics-service/`) | all pass, incl. new suite |
| TMS suite untouched | `pytest -q` (`services/test-management-service/`) | same green as `richardh` |
| Lint | `ruff check .` (both touched services) | clean |
| Compose smoke | `docker compose up -d --build --wait` then: login as `student1@revature.com` via gateway → `GET /v1/api/reports/user/{id}` and `…/attempts?size=5` through `:8000` with Bearer JWT | 200s, envelope shapes match schemas; `reporting-and-analytics-service` healthy with both engines |

## Requirements review (final milestone)

- Re-read detail-doc Steps 1–6 + spec §1 implementation details; confirm each
  with file:line + commit evidence. Step 1's "migration" is satisfied by the
  documented no-new-tables decision (ADR) with `0001` unchanged — call this out
  explicitly.
- Update `docs/features/w4-f1-results-reporting-endpoints.md` (✅ steps,
  evidence, Remaining → none) and the `FEATURE_STATUS.md` W4-F1 row + header
  note, same branch.
- Commit: `docs(w4-f1): requirements review — mark feature complete`.

## Push gate

Push `richardh-feat-W4F1` to origin **only if** every check in Testing &
validation passes **and** the requirements review confirms all six Steps.
Otherwise stop, leave the branch local, report what's outstanding.
