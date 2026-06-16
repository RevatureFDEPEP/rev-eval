# Feature Status Tracker

Summary of implementation state for the candidate features defined in the
curriculum spec files (`days_*_features.md` at the workspace root, one level
above this repo). Covers the full program, **Days 6–20** (Weeks 2–4).

Each feature has a detail file under [`docs/features/`](features/) with a
step-wise checklist, evidence (file paths, PRs, commits), and remaining work.
This file stays at summary level only — the **Notes** column gives the one-line
"what landed + where" per feature; the detail file is the full record.

> **Workflow:** this tracker is part of the feature delivery loop. When you
> start, advance, or finish a feature, update its detail file (check off steps,
> add evidence) **and** its status row here, in the same PR as the code change.

**Last assessed:** 2026-06-15 — **program complete**: all Week 2–4 features ✅.

## Status values

| Status | Meaning |
|---|---|
| ✅ Completed | All spec acceptance criteria met |
| 🟡 In Progress | Some steps done; open items listed in the detail file |
| ❌ Not Started | No meaningful implementation in the repo |

## Days 6–10 (Week 2 — platform hardening & question bank)

Spec: `days_6_10_features.md`.

| # | Feature | Spec priority | Status | Detail | Notes |
|---|---|---|---|---|---|
| W2-F1 | Nginx path-based routing & local TLS | REQUIRED | ✅ Completed | [detail](features/w2-f1-nginx-routing-tls.md) | Gateway path-based routing + local TLS certs (the Day-6 nginx wiring). |
| W2-F2 | Unit test scaffolding (frontend + backend) | — | ✅ Completed | [detail](features/w2-f2-unit-test-scaffolding.md) | Branch `richardh-feat-W2-F2`: multi-stage Dockerfiles + model/repo test depth + hermetic test DBs. |
| W2-F3 | Centralized log aggregation (Loki/Grafana) | — | ✅ Completed | [detail](features/w2-f3-log-aggregation.md) | Loki + Grafana centralized log aggregation. |
| W2-F4 | CI quality gates (Ruff / ESLint / Trivy / coverage) | REQUIRED | ✅ Completed | [detail](features/w2-f4-ci-quality-gates.md) | PR #40: Ruff / ESLint / Trivy / coverage gates in CI. |
| W2-F5 | Direct-to-MinIO diagram uploads (pre-signed URLs) | — | ✅ Completed | [detail](features/w2-f5-minio-presigned-uploads.md) | PR #49: pre-signed direct-to-MinIO upload URLs. |
| W2-F6 | Structured question authoring interface | — | ✅ Completed | [detail](features/w2-f6-question-authoring-ui.md) | Structured question authoring + validation UI. |
| W2-F7 | Alembic migrations & Category domain | — | ✅ Completed | [detail](features/w2-f7-alembic-category-domain.md) | Branch `richardh-feat-alembic`: Alembic migration chain + Category domain (also fixed gateway 204). |
| W2-F8 | Pre-existing defect cleanup (found during W2-F7) | — | ✅ Completed | [detail](features/w2-f8-pre-existing-defects.md) | PR #63: skills-500, user-service dual-engine, Pydantic-v2 sweep. |
| W2-M10 | Day 10 milestone: reporting service scaffold | milestone | ✅ Completed | [detail](features/w2-m10-reporting-service-scaffold.md) | PR #70: reporting service on its own `reporting-postgres`, empty Alembic `0001` baseline. Pairs with W2-F7's Alembic work. |

## Days 11–15 (Week 3 — quiz-taking vertical slice)

Spec: `days_11_15_features.md`. Built strictly with Day 1–15 concepts, in
dependency order: W3-F1 backend first → W3-F2 scoring/locking → W3-F3/F4
frontend that consumes it → W3-F5/F6 verification last.

| # | Feature | Day | Status | Detail | Notes |
|---|---|---|---|---|---|
| W3-F1 | Quiz session creation backend (`POST /sessions`, httpx integration) | 11 | ✅ Completed | [detail](features/w3-f1-quiz-session-backend.md) | PR #72: `POST /sessions` + httpx question sampling; Alembic `0004`. Strict prerequisite for the whole Week 3 slice. |
| W3-F2 | Scoring engine + attempt locking (idempotency, state machine) | 12 | ✅ Completed | [detail](features/w3-f2-scoring-engine-locking.md) | PR #74: `SELECT FOR UPDATE` locking, idempotency-key replay, attempt state machine; Jaccard partial-credit (**ADR 0002**). |
| W3-F3 | Test-taking frontend skeleton (`/take/[testId]`, AuthContext) | 13 | ✅ Completed | [detail](features/w3-f3-test-taking-frontend-skeleton.md) | PR #75: `/take/[testId]` skeleton + AuthContext. |
| W3-F4 | Auto-saving exam client (server timer, autosave, submit-lock) | 14 | ✅ Completed (re-open closed by W3-F7) | [detail](features/w3-f4-autosave-exam-client.md) | PR #76: server-anchored countdown, debounced `PATCH /sessions/{id}/draft` (Alembic `0006`), submit-lock `useReducer`. |
| W3-F5 | Integration tests vs. real Postgres/Mongo | 15 | ✅ Completed | [detail](features/w3-f5-integration-tests-real-db.md) | PR #79: `--integration` pytest suite vs real Postgres/Mongo — proves the concurrent-answer 200/409 + idempotency-replay claims; CI integration job. |
| W3-F6 | Playwright E2E happy path + smoke script | 15 | ✅ Completed | [detail](features/w3-f6-playwright-e2e-smoke.md) | PR #91: Playwright login→take→lock happy path + `smoke.sh` health-gate + e2e seed; CI e2e job. Score-summary adapted (finalize never writes `test_submissions` — deferred to W4 reporting). |
| W3-F7 | Week-3 review-findings remediation (trainer-defined) | — | ✅ Completed | [detail](features/w3-f7-review-remediation.md) | PRs #80, #81: nine items — ref-anchored timer, submit-retry, ACTIVE-session reuse (Alembic `0007` partial unique index), `/questions/sample` role gate, error/not-found routes, autosave max-wait. |

## Days 16–20 (Week 4 — reporting, RBAC & trainer dashboard)

Spec: `days_16_20_features.md`. Completes the vertical slice: candidate results
→ trainer aggregate reporting → role-based authorization. Dependency order
(W4-F1 first, W4-F5 last).

| # | Feature | Day | Status | Detail | Notes |
|---|---|---|---|---|---|
| W4-F1 | Candidate results reporting endpoints (filtering + pagination) | 16 | ✅ Completed | [detail](features/w4-f1-results-reporting-endpoints.md) | PR #103: reporting reads TMS `sessions`/`answers`/`tests` over a read-only second engine (shared-DB, **ADR 0001**); `GET /reports/user/{id}` (+`/attempts`) one-round-trip aggregates + pagination; gateway routes `/v1/api/reports`→:8004. Resolves W3-F6's score-visibility gap. |
| W4-F2 | Candidate results page (Suspense, error boundaries, chart) | 17 | ✅ Completed | [detail](features/w4-f2-candidate-results-page.md) | PR #106: `/results/[sessionId]` parallel-route layout — per-region `loading`/`error` boundaries, server-side fetch with JWT, `<ChartWrapper>` (the W4-F4 reuse surface) + `ScoreTrendChart`. |
| W4-F3 | Role-based authz (API) + aggregate reporting queries | 18 | ✅ Completed | [detail](features/w4-f3-rbac-aggregate-queries.md) | PR #109: reporting re-verifies the JWT itself (defense-in-depth) — `require_trainer` 401/403, TRAINER-only, ignores `X-User-*`. `GET /reports/aggregate` (GROUP BY test, pass rate, `percentile_cont` median) + `/reports/test/{id}/questions`. |
| W4-F4 | Trainer dashboard frontend (server RBAC, URL-synced filters) | 19 | ✅ Completed | [detail](features/w4-f4-trainer-dashboard-frontend.md) | PR #120: `/admin/dashboard` parallel-route — per-panel `loading`/`error`, server RBAC via shared `resolveAccess` (Edge middleware + `getSession`), new `GET /reports/timeseries` line chart, URL-synced debounced filters. |
| W4-F5 | Technical debt audit + ADR documentation | 20 | ✅ Completed | [detail](features/w4-f5-tech-debt-audit-adrs.md) | Branch `richardh-feat-W4F5`: debt inventory + repayment backlog (`docs/technical-debt.md`), ADR 0002 (ADR 0001 landed in W4-F1), AI-assistance disclosure/annotations, technical narrative. **Program complete.** |
