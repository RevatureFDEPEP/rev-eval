# W4-F3 — Role-Based Authorization (API Layer) + Aggregate Reporting Queries

**Feature:** [docs/features/w4-f3-rbac-aggregate-queries.md](../features/w4-f3-rbac-aggregate-queries.md)
**Spec:** `days_16_20_features.md` §3 (Day 18)
**Depends on:** W4-F1 (✅ merged, PR #103 — reporting endpoints + read-only TMS engine), W3-F2 (✅ — `answers.score`/`is_correct` populated by the scoring engine)
**Unblocks:** W4-F4 (trainer dashboard fetches these gated endpoints)
**Branch:** `richardh-feat-W4F3` off `richardh`

## Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Role gate | `role == "TRAINER"` only; everything else 403 | Spec verbatim ("403 when the verified role claim ≠ TRAINER"). ADMIN deliberately excluded; widening is a one-line change if W4-F4 needs it. |
| Missing/malformed `Authorization` | **401** (no credentials ≠ wrong role) | HTTP semantics; bad signature / expired `exp` also 401; only a *verified* non-trainer claim earns 403. |
| Median time-to-complete | `percentile_cont(0.5) WITHIN GROUP` on Postgres; portable ROW_NUMBER median fallback on sqlite | Spec demands `percentile_cont`; the aiosqlite unit-test fixture can't parse `WITHIN GROUP`. Mirrors the existing `_duration_seconds()` dialect branch (report_repository.py:29). Live compose smoke proves the real Postgres path. |
| Pass threshold | `REPORT_PASS_THRESHOLD` setting, default `70.0` | Spec: "configurable threshold". Env-overridable via pydantic-settings. |
| Histogram | 4 fixed buckets over per-answer score fractions: [0–0.25), [0.25–0.5), [0.5–0.75), [0.75–1.0] via `sum(case(...))` | Portable across both dialects, no dialect branch needed. |
| Per-question grouping | `GROUP BY question_id` (Mongo `_id`) | `question_index` varies per session (random sampling); `question_id` is the stable identity. |
| Mirror columns | Add `question_id`, `is_correct` to `TmsAnswer` read-only mapping | Columns already exist in TMS (`answer.py:18-42`); reporting's Alembic stays at `0001` head — TMS owns the schema, this is mapping-only. |
| Aggregate filters | Optional `test_id`, `date_from`, `date_to`, `min_attempts` (HAVING) on `/reports/aggregate` | W4-F4's dashboard appends filter params to this endpoint; `min_attempts` supplies the spec's HAVING clause. |
| Aggregate scope | SUBMITTED sessions only | Consistent with W4-F1's summary/attempts semantics — partial averages on ACTIVE sessions would read as final scores. |

## Context

- W4-F1 gave the reporting service a second read-only async engine over
  test-management's tables (`src/db/session.py:52`, `get_tms_db`), read-only
  mappings in `src/models/tms_readonly.py` (TmsTest/TmsSession/TmsAnswer), and
  two ungated endpoints under `/v1/api/reports/user/...`.
- **No JWT anywhere in the service today:** `python-jose` is not in
  `requirements.txt`, `JWT_SECRET` is in neither `src/config/settings.py` nor
  the service's docker-compose env block. All three must be added.
- The gateway forwards the original request headers downstream (it strips only
  host/content-length/x-forwarded-*, `main.py:212-228`), so the `Authorization`
  Bearer token reaches the reporting service intact — `require_trainer` can
  independently verify it. Gateway `ROUTES` already matches
  `^/v1/api/reports(/.*)?$` → reporting (main.py:60); **no ROUTES change
  needed** for the two new paths.
- JWT contract (user-service `auth_route.py:17-24`, `settings.py:20-23`):
  HS256, payload `{"sub": str(id), "email", "role": "TRAINER"|"ADMIN"|"PARTICIPANT", "exp"}`,
  secret env `JWT_SECRET`.
- Scoring data (W3-F2): `answers` rows carry `score` (Float [0,1] fraction),
  `is_correct` (Boolean), `question_id` (Mongo id), `question_index`;
  per-session score = `AVG(score) * 100` (`_session_score_subquery()`).
- Test fixture: `tests/conftest.py` builds in-memory aiosqlite TmsBase tables
  with deterministic seed sessions S1–S5; `client` fixture overrides
  `get_tms_db` over ASGITransport.
- **This is the first service to re-verify the JWT** (defense-in-depth) — the
  gateway remains the platform-wide auth boundary; document the posture.

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W4F3`** off `richardh` before any code change.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — `require_trainer` dependency + wiring

Files: `services/reporting-and-analytics-service/requirements.txt`,
`src/config/settings.py`, `src/v1/dependencies/auth.py` (new),
`docker-compose.yml`, `.env.example` (only if JWT_SECRET absent).

- Add `python-jose[cryptography]` to requirements.
- Settings: `JWT_SECRET: str = "dev-secret-change-me"` +
  `JWT_ALGORITHM: str = "HS256"` + `REPORT_PASS_THRESHOLD: float = 70.0`
  (defaults match user-service's so local dev works out of the box).
- `require_trainer(authorization: str = Header(None))`:
  - missing / non-`Bearer` header → **401**;
  - `jose.jwt.decode(token, JWT_SECRET, algorithms=["HS256"])` — `JWTError`
    (bad signature, expired `exp`) → **401**;
  - verified payload `role != "TRAINER"` → **403**;
  - returns the verified claims dict. Role read **only** from the verified
    payload — never from request body or `X-User-Role`. Docstring states the
    defense-in-depth posture explicitly.
- docker-compose.yml: add `JWT_SECRET: ${JWT_SECRET:-...}` to the
  reporting-and-analytics-service environment (same interpolation pattern as
  user-service/gateway).
- Commit: `feat(w4-f3): require_trainer JWT dependency (defense-in-depth)`

### M2 — `GET /reports/aggregate` (gated)

Files: `src/models/tms_readonly.py`, `src/repositories/report_repository.py`,
`src/services/report_service.py`, `src/schemas/report_schema.py`,
`src/v1/routes/report_route.py`.

- Extend `TmsAnswer` mapping with `question_id` (String), `is_correct`
  (Boolean) — mapping-only, no migration.
- Schema: `AggregateQuery` (optional `test_id`, `date_from`, `date_to`,
  `min_attempts: int | None` — same Pydantic-dataclass query-param pattern as
  `AttemptsQuery`); `TestAggregateRow` (test_id, test_name, total_attempts,
  distinct_candidates, avg_score, pass_rate, median_duration_seconds);
  response `{items: [...], pass_threshold: float}` so the frontend can label
  the pass-rate column.
- Repository `aggregate_by_test()` — one statement, GROUP BY test_id over
  SUBMITTED sessions joined to the per-session score subquery:
  - `func.count(session_id)` attempts, `func.count(distinct(user_id))`
    candidates, `func.avg(score)`,
  - pass rate = `avg(case(score >= threshold, 1.0, else 0.0)) * 100`,
  - median duration: dialect branch — Postgres
    `func.percentile_cont(0.5).within_group(duration)`; sqlite ROW_NUMBER/COUNT
    portable median (same shape as `_duration_seconds`),
  - `HAVING count(*) >= min_attempts` when provided; date/test filters reuse
    `_apply_filters` semantics.
- Route `GET /reports/aggregate`, `dependencies=[Depends(require_trainer)]`.
- Commit: `feat(w4-f3): trainer aggregate report (GROUP BY/HAVING + percentile_cont)`

### M3 — `GET /reports/test/{test_id}/questions` (gated)

Files: repository, service, schemas, route (same four).

- Repository `question_difficulty(test_id)` — inner GROUP BY `question_id`
  over answers joined to SUBMITTED sessions of that test: attempts,
  `correct_rate = avg(case(is_correct, 1.0, 0.0)) * 100`, histogram buckets
  `sum(case(score < .25, 1))` … `sum(case(score >= .75, 1))`; outer select adds
  `RANK() OVER (ORDER BY correct_rate ASC)` (hardest = rank 1) — plain window
  function, works on both dialects.
- 404 when `test_id` doesn't exist in `tests`.
- Schema: `QuestionDifficultyRow` (question_id, attempts, correct_rate,
  difficulty_rank, histogram: {bucket label → count}); envelope with test
  id/name.
- Route gated by `require_trainer`.
- Commit: `feat(w4-f3): per-question difficulty report (RANK + histogram)`

### M4 — Unit tests + defense-in-depth posture

Files: `tests/conftest.py`, `tests/test_auth_dependency.py` (new),
`tests/test_aggregate_endpoints.py` (new), feature detail doc (posture note).

- Conftest: seed gains `question_id`/`is_correct` on answers (+ a second test
  with divergent correct-rates so RANK ordering is assertable); token factory
  fixture minting real HS256 tokens (trainer / participant / expired / wrong
  secret) against the test settings' `JWT_SECRET`.
- Gate tests (real tokens, no override — this *is* the unit under test):
  missing header → 401, garbage/wrong-secret token → 401, expired → 401,
  PARTICIPANT → 403, ADMIN → 403, TRAINER → 200.
- Endpoint tests (dependency override for `require_trainer`, per spec):
  aggregate row values from the seed (attempts, distinct candidates,
  avg, pass rate at threshold, sqlite-median), HAVING `min_attempts` drops
  thin groups, filters; questions endpoint correct_rate, rank order
  (hardest first), histogram counts, unknown test → 404.
- Defense-in-depth ("curl-equivalent, bypassing all frontend guards"): test
  posting straight to the ASGI app with spoofed `X-User-Role: TRAINER` headers
  but a PARTICIPANT (or absent) Bearer token → 403/401 — proves the gate
  ignores gateway headers. Posture paragraph added to the feature detail doc.
- Commit: `test(w4-f3): RBAC gate matrix + aggregate query unit tests`

### M5 — Live compose smoke (gateway awareness + real percentile_cont)

No code; evidence captured for the requirements review.

- `docker compose up -d --build --wait`, seed via `scripts/e2e-seed.sh` +
  take/submit an attempt if needed.
- Through the gateway (`:8000`): login as trainer → `GET /v1/api/reports/aggregate`
  → 200 with real rows (exercises Postgres `percentile_cont`); participant
  token → 403; no token → 401 (gateway boundary).
- Direct to the service (`:8004`): spoofed `X-User-Role: TRAINER`, no/participant
  JWT → 401/403 — independent enforcement demonstrated outside the gateway.
- `GET /reports/test/{id}/questions` → 200 with rank + histogram.

### M6 — Requirements review + docs

Files: `docs/features/w4-f3-rbac-aggregate-queries.md`,
`docs/FEATURE_STATUS.md`.

- Re-read the 5 Steps + spec §3 Implementation Details; verify each against
  the diff with file:line + commit evidence; check off steps in the detail
  doc, record the M5 smoke transcript, note the ADMIN-excluded decision and
  the sqlite-median fallback as recorded deviations.
- Flip FEATURE_STATUS.md row W4-F3 → ✅ + update the "Last assessed" summary.
- Commit: `docs(w4-f3): requirements review — mark feature complete`

## Testing & validation

| Check | Command (from) | Pass bar |
|---|---|---|
| Reporting unit tests | `pytest --cov` (`services/reporting-and-analytics-service/`) | All pass (20 existing + new gate matrix & aggregate tests); no regressions |
| Gateway tests | `pytest` (`services/api-gateway-service/`) | 51 pass, unchanged |
| Live smoke | `docker compose up -d --build --wait` + M5 curl matrix | trainer 200 / participant 403 / no-token 401 via gateway; direct-:8004 spoofed-header rejection; real `percentile_cont` row values |

## Push gate

Push `richardh-feat-W4F3` to origin **only if** all tests pass **and** the M6
review confirms every Step. Otherwise stop, leave the branch local, report
what's outstanding.

## Out of scope (noted for later features)

- Frontend consumption of these endpoints, attempt-volume-over-time series,
  URL-synced filters — W4-F4.
- Retrofitting `require_trainer`-style verification onto other services —
  candidate for the W4-F5 debt inventory.
- W4-F1's user endpoints stay ungated (candidates must read their own
  results); per-user authorization (self-or-trainer) is a W4-F5 debt note.
