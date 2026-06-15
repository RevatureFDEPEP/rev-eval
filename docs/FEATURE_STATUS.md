# Feature Status Tracker

Summary of implementation state for the candidate features defined in the
curriculum spec files (`days_*_features.md` at the workspace root, one level
above this repo). Covers the full program, **Days 6–20** (Weeks 2–4).

Each feature has a detail file under [`docs/features/`](features/) with a
step-wise checklist, evidence (file paths, PRs, commits), and remaining work.
This file stays at summary level only.

> **Workflow:** this tracker is part of the feature delivery loop. When you
> start, advance, or finish a feature, update its detail file (check off steps,
> add evidence) **and** its status row here, in the same PR as the code change.

**Last assessed:** 2026-06-15 (**W4-F5 completed** — Day 20 capstone audit on
`richardh-feat-W4F5`, the final feature in the program: a docs-only reflective
deliverable (only code change is comment-only AI-assistance annotations on 4
seams — 10 insertions, 0 deletions). `docs/technical-debt.md` inventories
shortcuts in 8 categories (each row: name · file:line · condition-under-which-
it-matters · urgency vs. current local-first scale) and closes with a
prioritized repayment backlog — high-urgency security items (`JWT_SECRET`
default, CORS `*`) lead, then migration coverage, pagination, header-trust
hardening, validation, cruft. Two ADRs satisfy the spec's required pair:
`0001` (reporting reads TMS Postgres directly — written during W4-F1) and the
new `0002` (multi-select Jaccard scoring vs. all-or-nothing / correct-minus-
wrong — lifted from W3-F2's `partial_credit.py` docstring). `docs/ai-assistance.md`
discloses the AI-assisted-under-human-review workflow, documents the inline
annotation convention, and carries a per-section verbal defence; the narrative
(`docs/technical-narrative.md`) tells reporting (→0001) and scoring (→0002) as
what/why/how. Validation: `pnpm lint` 0 errors, `pnpm build` clean, code diff
comment-only/all-additive. **Program complete: all 22 features ✅.** Prior:
**W4-F4 completed** — trainer dashboard on
`richardh-feat-W4F4`: `/admin/dashboard` is a parallel-route page (mirrors
W4-F2) whose two data regions — pass-rate-per-test bar chart (`/reports/aggregate`)
and attempt-volume-over-time line chart — each carry their own `loading.tsx`
skeleton + `SectionErrorFallback` boundary, so one failing/403 reporting call
blanks only its panel. Server-side RBAC is the gate: a shared pure
`resolveAccess` helper (`lib/auth/access.ts`) drives both the Edge middleware
and the layout/page `getSession` re-check — `/admin` is **TRAINER-only**
(matching W4-F3's backend gate; ADMIN redirected, not walled behind a 403);
the AuthContext-gated "Analytics" nav link is an explicit UX-affordance only.
Filters (`DashboardFilters`) write `test_id`/`from`/`to` to the query string
(URL-shareable) via `router.replace` — dropdown immediate, date inputs
debounced 300ms (dependency-free `useDebouncedCallback`); the slot server
components read `searchParams` and fetch server-side (no flicker). The line
chart is fed by a **new `GET /reports/timeseries`** (require_trainer-gated,
GROUP BY day(submitted_at), test_id) added to the reporting service —
`/aggregate` is collapsed per-test with no date axis; additive/zero-risk since
nothing else consumes the service. Pure `pivotVolumeByTest` derives a total
line + one line per quiz, collapsing to one series when a test is filtered.
Reporting suite 45 (5 timeseries tests added over the aiosqlite fixture);
frontend 154 (was 130: resolver matrix, URL-sync+debounce, chart transforms,
EmptyState) + lint/build clean; live smoke: trainer dashboard 200 server-
rendered with real data, participant 307→/unauthorized, no-cookie 307→/,
timeseries 200/403/401 + filter via gateway. Prior: **W4-F3 completed** — RBAC + aggregate
reporting on `richardh-feat-W4F3`: the reporting service is the first to
re-verify the JWT itself (defense-in-depth) — `require_trainer`
(`src/v1/dependencies/auth.py`, python-jose + shared `JWT_SECRET`) returns 401
on missing/invalid/expired tokens and 403 unless the *verified* role claim is
TRAINER (spec-strict: ADMIN excluded), never reading role from `X-User-*`
headers — spoofed-header curls straight to :8004 are rejected, proven in unit
tests and live. Two gated endpoints: `GET /reports/aggregate` GROUPs SUBMITTED
sessions BY test (attempts, distinct candidates, avg score, pass rate vs. the
configurable `REPORT_PASS_THRESHOLD`, median time-to-complete via
`percentile_cont WITHIN GROUP` on Postgres with a portable ROW_NUMBER median
on the sqlite fixture; `min_attempts` renders as HAVING, plus test/date
filters for the W4-F4 dashboard) and `GET /reports/test/{id}/questions`
(per-question correct rate grouped by the stable Mongo question_id, hardest-
first `RANK() OVER (ORDER BY correct_rate ASC)`, 4-bucket partial-credit
histogram, 404 on unknown test). `TmsAnswer` mirror gained
`question_id`/`is_correct` (mapping-only). Reporting suite 40 passed / 92.62%
cov (gate matrix with real HS256 tokens + aggregate value tests); gateway 51
unchanged (`^/v1/api/reports` already routes, Authorization forwarded); live
smoke: trainer 200 with real `percentile_cont` (median 26.81s), participant
403, no-token 401, HAVING/422/404 verified. Prior: **W4-F2 completed** — candidate results page on
`richardh-feat-W4F2`: `/results/[sessionId]` is a parallel-route layout whose
three data regions (summary headline, attempts table, score chart) each carry
their own `loading.tsx` skeleton and `error.tsx` boundary, so chrome streams on
first byte and a reporting-service outage blanks only the failing panels —
Playwright smoke confirmed 3 isolated fallbacks with working Retry
(`router.refresh()` + `reset()`) recovery. All data is fetched server-side from
the W4-F1 endpoints with the `auth_token` JWT (`getUserReportSummaryServer` /
`getUserReportAttemptsServer`); the `[sessionId]` param highlights that attempt.
`<ChartWrapper>` (ResponsiveContainer + `role="img"`/aria-label + shared
tooltip/legend props) is the W4-F4 reuse surface; `ScoreTrendChart` renders the
score-per-attempt BarChart. Table is per-attempt, not per-question — the W4-F1
API exposes no per-question data (deviation recorded in the detail doc).
`pnpm lint` 0 errors, `pnpm build` clean. Prior: **W4-F1 completed** — candidate results
reporting endpoints on `richardh-feat-W4F1`: the reporting service reads
test-management's `sessions`/`answers`/`tests` directly over a second
read-only async engine (the shared-DB pattern, recorded with its alternatives
in `docs/adr/0001-reporting-cross-service-data-access.md` — one of W4-F5's two
required ADRs; no reporting-side tables, Alembic `0001` stays head).
`GET /reports/user/{id}` aggregates total/avg/best/time + most-recent attempt
in one SQL round trip; `GET /reports/user/{id}/attempts` paginates with
`AttemptsQuery` (test/date/status filters, whitelisted `field:direction` sort,
NULLs last) returning `{items,total,page,size}`; gateway routes
`/v1/api/reports` → :8004. This resolves W3-F6's rolled-in gap: scores become
user-visible via these endpoints (W4-F2 renders them), not by bridging
finalize → `test_submissions`. Reporting 20 tests (17 new over an aiosqlite
TmsBase fixture), gateway 51, TMS 100+6 unchanged; live compose smoke returned
a real attempt (33.33%, 26.81s) through the gateway with filters/422/401
verified. Prior: **W3-F6 completed** — Week 3 slice closed on
`richardh-feat-W3F6`: Playwright happy path drives login → dashboard → Start →
count-agnostic answer loop → locked confirmation through the W3-F4 TestRunner
(dashboard quiz links rewired from the legacy mcq page to `/take/[testId]`),
green twice against the live compose stack; `scripts/smoke.sh` gates on every
`/health` in dependency order (negative check verified) and
`scripts/e2e-seed.sh` idempotently seeds the Mongo question bank; CI gains a
sequential `e2e` job (throwaway nginx certs, `compose up -d --build --wait`,
seed → smoke → Playwright) uploading `e2e-run.log` + the Playwright report as
artifacts. Spec's score-summary assertion deliberately adapted: session
finalize never writes `test_submissions` — gap documented in the feature doc
for the W4 reporting slice; E2E also surfaced legacy option-less true_false
bank docs rendering "No options available" in TestRunner, noted as a cleanup
candidate. Frontend 130 units + lint/build green. Prior: **W3-F7 completed** — all nine review-remediation
items landed on `richardh-feat-W3F7`, closing the W3-F4 re-open: the
`useServerTimer` deadline is anchored once in a ref (countdown survives submit
toggles; disable→re-enable regression specs added), `SUBMIT_RETRY` gives a
transient-only exit from the submit-error lock, `POST /sessions` reuses the
ACTIVE session per (user, test) with Alembic `0007`'s partial unique index as
the race backstop (loser serves the winner's row), `GET /questions/sample`
rejects non-TRAINER/ADMIN roles (headerless internal calls pass),
`/take/[testId]` gains `error.tsx`/`not-found.tsx`, autosave gets a max-wait
cap + semantic-409/410 halt, question groups are `aria-labelledby`-associated,
sampled question ids are deduped with short-fill warnings, and the
idempotency/lock contracts are documented. Frontend 130 tests + lint/build
green; TMS 100 unit + 6 integration vs real Postgres/Mongo; QMS 35; live
compose smoke verified the role gate (403/200) and double-POST reuse (one
ACTIVE row). **W3-F4 flips back to ✅.** Prior: W3-F5 completed — integration suite against real
containers: a `--integration`-gated pytest suite in test-management-service
provisions a dedicated `eval_ai_itest` Postgres database per run (drop/create +
`alembic upgrade head`), runs the app in-process over ASGI with per-request
sessions, and seeds the question bank directly in Mongo so `POST /sessions`
exercises the real httpx → question-management-service → `$sample` path. Proves
the W3-F2 claims only real Postgres can: two concurrent answers to a
single-question session → exactly one 200 + one 409 with `current_index`
advanced once (`SELECT FOR UPDATE`), and same-`Idempotency-Key` retry → replayed
body, one mutation. CI runs it in the test-management-service matrix entry via
`docker compose up -d --wait postgres mongo question-management-service` before
the Docker build. 4 integration tests pass; unit suite unchanged (94 passed,
4 skipped without the flag); Docker `test` stage stays hermetic. W3-F4 prior:
auto-saving exam client — server-anchored countdown, debounced autosave to
`PATCH /sessions/{id}/draft` (Alembic `0006`), error classification + backoff,
submit-and-lock `useReducer`; frontend 116 tests, lint/build green.)

## Status values

| Status | Meaning |
|---|---|
| ✅ Completed | All spec acceptance criteria met |
| 🟡 In Progress | Some steps done; open items listed in the detail file |
| ❌ Not Started | No meaningful implementation in the repo |

## Days 6–10 (Week 2 — platform hardening & question bank)

Spec: `days_6_10_features.md`.

| # | Feature | Spec priority | Status | Detail |
|---|---|---|---|---|
| W2-F1 | Nginx path-based routing & local TLS | REQUIRED | ✅ Completed | [w2-f1-nginx-routing-tls.md](features/w2-f1-nginx-routing-tls.md) |
| W2-F2 | Unit test scaffolding (frontend + backend) | — | ✅ Completed | [w2-f2-unit-test-scaffolding.md](features/w2-f2-unit-test-scaffolding.md) |
| W2-F3 | Centralized log aggregation (Loki/Grafana) | — | ✅ Completed | [w2-f3-log-aggregation.md](features/w2-f3-log-aggregation.md) |
| W2-F4 | CI quality gates (Ruff / ESLint / Trivy / coverage) | REQUIRED | ✅ Completed | [w2-f4-ci-quality-gates.md](features/w2-f4-ci-quality-gates.md) |
| W2-F5 | Direct-to-MinIO diagram uploads (pre-signed URLs) | — | ✅ Completed | [w2-f5-minio-presigned-uploads.md](features/w2-f5-minio-presigned-uploads.md) |
| W2-F6 | Structured question authoring interface | — | ✅ Completed | [w2-f6-question-authoring-ui.md](features/w2-f6-question-authoring-ui.md) |
| W2-F7 | Alembic migrations & Category domain | — | ✅ Completed | [w2-f7-alembic-category-domain.md](features/w2-f7-alembic-category-domain.md) |
| W2-F8 | Pre-existing defect cleanup (found during W2-F7) | — | ✅ Completed | [w2-f8-pre-existing-defects.md](features/w2-f8-pre-existing-defects.md) |
| W2-M10 | Day 10 milestone: reporting service scaffold | milestone | ✅ Completed | [w2-m10-reporting-service-scaffold.md](features/w2-m10-reporting-service-scaffold.md) |

## Days 11–15 (Week 3 — quiz-taking vertical slice)

Spec: `days_11_15_features.md`. Built strictly with Day 1–15 concepts; listed
in dependency order (W3-F1 first, W3-F6 last).

| # | Feature | Day | Status | Detail |
|---|---|---|---|---|
| W3-F1 | Quiz session creation backend (`POST /sessions`, httpx integration) | 11 | ✅ Completed | [w3-f1-quiz-session-backend.md](features/w3-f1-quiz-session-backend.md) |
| W3-F2 | Scoring engine + attempt locking (idempotency, state machine) | 12 | ✅ Completed | [w3-f2-scoring-engine-locking.md](features/w3-f2-scoring-engine-locking.md) |
| W3-F3 | Test-taking frontend skeleton (`/take/[testId]`, AuthContext) | 13 | ✅ Completed | [w3-f3-test-taking-frontend-skeleton.md](features/w3-f3-test-taking-frontend-skeleton.md) |
| W3-F4 | Auto-saving exam client (server timer, autosave, submit-lock) | 14 | ✅ Completed (re-open closed by W3-F7 item 1) | [w3-f4-autosave-exam-client.md](features/w3-f4-autosave-exam-client.md) |
| W3-F5 | Integration tests vs. real Postgres/Mongo | 15 | ✅ Completed | [w3-f5-integration-tests-real-db.md](features/w3-f5-integration-tests-real-db.md) |
| W3-F6 | Playwright E2E happy path + smoke script | 15 | ✅ Completed | [w3-f6-playwright-e2e-smoke.md](features/w3-f6-playwright-e2e-smoke.md) |
| W3-F7 | Week-3 review-findings remediation (trainer-defined) | — | ✅ Completed | [w3-f7-review-remediation.md](features/w3-f7-review-remediation.md) |

## Days 16–20 (Week 4 — reporting, RBAC & trainer dashboard)

Spec: `days_16_20_features.md`. Completes the vertical slice: candidate results
→ trainer aggregate reporting → role-based authorization. Dependency order
(W4-F1 first, W4-F5 last).

| # | Feature | Day | Status | Detail |
|---|---|---|---|---|
| W4-F1 | Candidate results reporting endpoints (filtering + pagination) | 16 | ✅ Completed | [w4-f1-results-reporting-endpoints.md](features/w4-f1-results-reporting-endpoints.md) |
| W4-F2 | Candidate results page (Suspense, error boundaries, chart) | 17 | ✅ Completed | [w4-f2-candidate-results-page.md](features/w4-f2-candidate-results-page.md) |
| W4-F3 | Role-based authz (API) + aggregate reporting queries | 18 | ✅ Completed | [w4-f3-rbac-aggregate-queries.md](features/w4-f3-rbac-aggregate-queries.md) |
| W4-F4 | Trainer dashboard frontend (server RBAC, URL-synced filters) | 19 | ✅ Completed | [w4-f4-trainer-dashboard-frontend.md](features/w4-f4-trainer-dashboard-frontend.md) |
| W4-F5 | Technical debt audit + ADR documentation | 20 | ✅ Completed | [w4-f5-tech-debt-audit-adrs.md](features/w4-f5-tech-debt-audit-adrs.md) |

## Suggested order of attack

1. ~~**W2-F4 finish**~~ — done (PR #40).
2. ~~**W2-F5 pre-signed uploads**~~ — done (PR #49).
3. ~~**W2-F7 Alembic + Category**~~ — done (branch `richardh-feat-alembic`).
4. ~~**W2-F2 deepen**~~ — done (branch `richardh-feat-W2-F2`): multi-stage Dockerfiles + model/repo test depth + hermetic test DBs.
5. **W2-M10 reporting scaffold** — pairs naturally with W2-F7's Alembic work.
6. ~~**W2-F8 defect cleanup**~~ — done (PR #63: skills-500, user-service dual-engine, Pydantic-v2 sweep; gateway 204 was in W2-F7).
7. **W3-F1 sessions backend** — strict prerequisite for the whole Week 3 slice; lands as Alembic `0004` on W2-F7's chain.
8. **W3-F2 → W3-F3 → W3-F4** — the quiz-taking slice in dependency order; W3-F2 backend before the W3-F3/W3-F4 frontend that consumes it.
9. ~~**W3-F5 + W3-F6**~~ — verification layer, done. (W3-F5 — PR #79; W3-F6 — branch `richardh-feat-W3F6`.)
9a. ~~**W3-F7 review remediation before W3-F6**~~ — done (branch `richardh-feat-W3F7`): timer fix + reuse semantics landed before the Playwright happy path; the `/questions/sample` role gate previews W4-F3.
10. ~~**W2-M10 → W4-F1 → W4-F3**~~ — done; RBAC gate + aggregate endpoints landed on `richardh-feat-W4F3`.
11. ~~**W4-F2 → W4-F4**~~ — done; trainer dashboard on `richardh-feat-W4F4` reuses `<ChartWrapper>`, adds the `/reports/timeseries` endpoint, server-side `/admin` RBAC, and URL-synced filters.
12. ~~**W4-F5 last**~~ — done (branch `richardh-feat-W4F5`): debt inventory + repayment backlog (`docs/technical-debt.md`), ADR 0002 (scoring; 0001 already landed in W4-F1), AI-assistance disclosure/annotations, technical narrative. The W4-F1 and W3-F2 ADR decisions were captured as those features landed, as planned. **Program complete.**
