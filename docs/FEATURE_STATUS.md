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

**Last assessed:** 2026-06-17 — **Tianya Chen (`tianyac` branch)**

Work completed across `tianyac-feat-nginx` (merged), `tianyac-feat-unit-test`
(PR #45 merged), `tianyac` CI pipeline commits, `tianyac-feat-session`
(W3-F1), `tianyac-alembic-migrations` (W2-F7), and `tianyac-scoring-engine`
(W3-F2). Documentation system added on `tianyac-feat-doc`: `docs/FEATURE_STATUS.md`
+ `docs/features/` detail files for all 21 features, replacing `docs/plans/`.

**Progress summary:** W3-F2 (scoring engine + attempt locking) ✅ complete on
`tianyac-scoring-engine` (PR #148, commit `5fc9c05`) — deterministic exact-match
and Jaccard partial-credit scoring, `POST /v1/api/sessions/{id}/answer` with
pessimistic locking + `begin_nested` SAVEPOINT for concurrent idempotency-key
dedup, session state machine (`IN_PROGRESS → SUBMITTED`), `ai_score` finalization
on last question, Alembic migration `0007` (`session_answers` + `idempotency_keys`),
22 pure-function tests + 6 httpx integration tests (161 total passing).
W3-F1 (quiz session backend) ✅ complete on `tianyac-feat-session` (commit
`ca6877d`); security hardened — `correct_answers` excluded by MongoDB `$project`.
W2-F7 (Alembic + Category domain + reporting scaffold) ✅ complete on
`tianyac-alembic-migrations` — migration `0005_add_categories`, full Category
CRUD stack at `/v1/api/categories`, reporting-and-analytics-service scaffold
with `reporting-postgres` + Alembic baseline, three defects fixed (skill-500,
user-service dual-engine, Pydantic v2 audit). W2-F1 (nginx TLS + basic routing),
W2-F2 (frontend + backend unit tests), W2-F4 (Ruff/ESLint CI gates), W2-F6
(question authoring schema + tests) partially done (🟡). All other W2, remaining
W3, and all W4 features not yet started on this branch.

**W2-F1** — nginx reverse proxy live: :80→:443 redirect, TLS, `/_next/` WebSocket
routing, `/→frontend`. Remaining: step 4 BFF bearer pattern (direct
`/api/v1/→gateway` block still present in `nginx.conf`; must route all data
calls through the Next.js BFF as the single auth-injection point), JSON access
logs, request-time DNS resolver (`127.0.0.11`), X-Correlation-Id header.

**W2-F2** — Jest 30 + `@testing-library/react` 16 frontend suite (102 tests:
quiz UI components, landing auth, Zod schemas, lib utilities) + backend
parameterized pytest for 3 services (test-management 121 tests, user-service
83 tests, question-management). Remaining: step 3 multi-stage Dockerfiles
(test stage not yet added — Dockerfiles are single-stage); api-gateway-service
tests not yet scaffolded.

**W2-F4** — Ruff linting and ESLint hard failure in CI, `pytest --cov` in the
backend matrix, path-filtered runs. Remaining: step 3 Trivy container scan
(not in `.github/workflows/ci-pipeline.yml`), per-service `.coveragerc`
`fail_under` ratchets (coverage runs but thresholds not enforced — no `.coveragerc`
files exist).

**W2-F6** — question create page (brownfield), question list page (brownfield),
Zod schema (`lib/schemas/question-form.ts`), 135-line schema test suite.
Remaining: extract `QuestionForm.tsx` shared component, wire gateway submit,
add file-upload field (blocked on W2-F5), edit page.

All W2-F3 (Loki/Grafana) and W2-F5 (MinIO presigned), and the full W3 and W4
slices are not yet started on Tianya's branch.

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
| W2-F1 | Nginx path-based routing & local TLS | REQUIRED | 🟡 In Progress | [w2-f1-nginx-routing-tls.md](features/w2-f1-nginx-routing-tls.md) |
| W2-F2 | Unit test scaffolding (frontend + backend) | — | 🟡 In Progress | [w2-f2-unit-test-scaffolding.md](features/w2-f2-unit-test-scaffolding.md) |
| W2-F3 | Centralized log aggregation (Loki/Grafana) | — | ❌ Not Started | [w2-f3-log-aggregation.md](features/w2-f3-log-aggregation.md) |
| W2-F4 | CI quality gates (Ruff / ESLint / Trivy / coverage) | REQUIRED | 🟡 In Progress | [w2-f4-ci-quality-gates.md](features/w2-f4-ci-quality-gates.md) |
| W2-F5 | Direct-to-MinIO diagram uploads (pre-signed URLs) | — | ❌ Not Started | [w2-f5-minio-presigned-uploads.md](features/w2-f5-minio-presigned-uploads.md) |
| W2-F6 | Structured question authoring interface | — | 🟡 In Progress | [w2-f6-question-authoring-ui.md](features/w2-f6-question-authoring-ui.md) |
| W2-F7 | Alembic migrations & Category domain + reporting service scaffold | — | ✅ Completed | [w2-f7-alembic-category-domain.md](features/w2-f7-alembic-category-domain.md) |

## Days 11–15 (Week 3 — quiz-taking vertical slice)

Spec: `days_11_15_features.md`. W3-F1 complete (`tianyac-feat-session`, commit
`ca6877d`). W3-F2 complete (`tianyac-scoring-engine`, PR #148, commit `5fc9c05`
— Alembic at head `0007`). W3-F3 through W3-F7 not yet started.

| # | Feature | Day | Status | Detail |
|---|---|---|---|---|
| W3-F1 | Quiz session creation backend (`POST /sessions`, httpx integration) | 11 | ✅ Completed | [w3-f1-quiz-session-backend.md](features/w3-f1-quiz-session-backend.md) |
| W3-F2 | Scoring engine + attempt locking (idempotency, state machine) | 12 | ✅ Completed | [w3-f2-scoring-engine-locking.md](features/w3-f2-scoring-engine-locking.md) |
| W3-F3 | Test-taking frontend skeleton (`/take/[testId]`, AuthContext) | 13 | ❌ Not Started | [w3-f3-test-taking-frontend-skeleton.md](features/w3-f3-test-taking-frontend-skeleton.md) |
| W3-F4 | Auto-saving exam client (server timer, autosave, submit-lock) | 14 | ❌ Not Started | [w3-f4-autosave-exam-client.md](features/w3-f4-autosave-exam-client.md) |
| W3-F5 | Integration tests vs. real Postgres/Mongo | 15 | ❌ Not Started | [w3-f5-integration-tests-real-db.md](features/w3-f5-integration-tests-real-db.md) |
| W3-F6 | Playwright E2E happy path + smoke script | 15 | ❌ Not Started | [w3-f6-playwright-e2e-smoke.md](features/w3-f6-playwright-e2e-smoke.md) |
| W3-F7 | Week-3 review-findings remediation (trainer-defined) | — | ❌ Not Started | [w3-f7-review-remediation.md](features/w3-f7-review-remediation.md) |

## Days 16–20 (Week 4 — reporting, RBAC & trainer dashboard)

Spec: `days_16_20_features.md`. Completes the vertical slice: candidate results
→ trainer aggregate reporting → role-based authorization. Dependency order
(W4-F1 first, W4-F5 last). W4-F1 complete (`tianyac-reporting-endpoints`,
commit `058d45c`).

| # | Feature | Day | Status | Detail |
|---|---|---|---|---|
| W4-F1 | Candidate results reporting endpoints (filtering + pagination) | 16 | ✅ Completed | [w4-f1-results-reporting-endpoints.md](features/w4-f1-results-reporting-endpoints.md) |
| W4-F2 | Candidate results page (Suspense, error boundaries, chart) | 17 | ❌ Not Started | [w4-f2-candidate-results-page.md](features/w4-f2-candidate-results-page.md) |
| W4-F3 | Role-based authz (API) + aggregate reporting queries | 18 | ❌ Not Started | [w4-f3-rbac-aggregate-queries.md](features/w4-f3-rbac-aggregate-queries.md) |
| W4-F4 | Trainer dashboard frontend (server RBAC, URL-synced filters) | 19 | ❌ Not Started | [w4-f4-trainer-dashboard-frontend.md](features/w4-f4-trainer-dashboard-frontend.md) |
| W4-F5 | Technical debt audit + ADR documentation | 20 | ❌ Not Started | [w4-f5-tech-debt-audit-adrs.md](features/w4-f5-tech-debt-audit-adrs.md) |

## Suggested order of attack

1. **W2-F1 finish** — add BFF bearer pattern: route all `/api/v1/*` through
   `frontend:3000` (the Next.js BFF injects the `Bearer` header), remove the
   direct nginx→gateway `location /api/v1/` block. Also add JSON access logs
   + `resolver 127.0.0.11` for Docker DNS.
2. **W2-F2 finish** — add multi-stage Dockerfiles (`base → test → production`)
   to all 4 backend services; the `test` stage runs `pytest -q` so CI can gate
   on `docker build --target test`.
3. **W2-F4 finish** — add Trivy container scan step to each backend matrix job
   (CRITICAL/HIGH, `exit-code: 1`, `ignore-unfixed: true`); add per-service
   `.coveragerc` with `fail_under` ratchets.
4. ~~**W2-F7 Alembic + Category + reporting scaffold**~~ — ✅ done on `tianyac-alembic-migrations`
   (Alembic head `0005`, Category CRUD, reporting scaffold, three defects fixed).
5. **W2-F5 pre-signed uploads** — MinIO boto3 pre-signed PUT endpoint + frontend
   file input; unblocks W2-F6 file upload step.
6. **W2-F6 finish** — extract `QuestionForm` component, wire file upload (W2-F5),
   add edit page.
7. **W2-F3 Loki/Grafana** — `observability/` compose stack (Loki + Promtail +
   Grafana); JSON log format + `X-Correlation-Id` in nginx and services.
8. **W3-F1 sessions backend** — `POST /sessions` + Alembic `0004`; first
   cross-service httpx call.
9. **W3-F2 → W3-F3 → W3-F4** — scoring engine, take-page skeleton, exam client;
   in dependency order.
10. **W3-F5 + W3-F6** — integration tests (real Postgres/Mongo) + Playwright E2E.
11. **W3-F7** — review-remediation items (timer fix, session reuse, role gate,
    error boundaries).
12. ~~**W4-F1**~~ ✅ done on `tianyac-reporting-endpoints` (commit `058d45c`). **W4-F3** — RBAC gate + aggregate endpoints extend the reporting scaffold.
13. **W4-F2 → W4-F4** — results page then trainer dashboard.
14. **W4-F5 last** — debt audit + ADRs; needs a substantially complete codebase.
