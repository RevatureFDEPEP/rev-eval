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

**Last assessed:** 2026-06-10 PM (post-merge review of the Week-3 PRs
#72/#74/#75/#76 re-opened **W3-F4** — `useServerTimer` re-anchors its wall-clock
baseline every time `enabled` toggles, and every submit toggles it, so the
countdown resets to the full session duration after question 1; client-side
auto-submit at expiry effectively never fires. The fix plus the review's
cross-feature follow-ups (active-session reuse, `GET /questions/sample`
role gate, take-page `error.tsx`, submit-retry affordance, autosave max-wait)
are specced as trainer-defined
**[W3-F7](features/w3-f7-review-remediation.md)**; W3-F4 completion is gated on
its item 1. Prior: W3-F5 completed — integration suite against real
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
| W3-F4 | Auto-saving exam client (server timer, autosave, submit-lock) | 14 | 🟡 In Progress (re-opened — timer defect, see W3-F7 item 1) | [w3-f4-autosave-exam-client.md](features/w3-f4-autosave-exam-client.md) |
| W3-F5 | Integration tests vs. real Postgres/Mongo | 15 | ✅ Completed | [w3-f5-integration-tests-real-db.md](features/w3-f5-integration-tests-real-db.md) |
| W3-F6 | Playwright E2E happy path + smoke script | 15 | ❌ Not Started | [w3-f6-playwright-e2e-smoke.md](features/w3-f6-playwright-e2e-smoke.md) |
| W3-F7 | Week-3 review-findings remediation (trainer-defined) | — | ❌ Not Started | [w3-f7-review-remediation.md](features/w3-f7-review-remediation.md) |

## Days 16–20 (Week 4 — reporting, RBAC & trainer dashboard)

Spec: `days_16_20_features.md`. Completes the vertical slice: candidate results
→ trainer aggregate reporting → role-based authorization. Dependency order
(W4-F1 first, W4-F5 last).

| # | Feature | Day | Status | Detail |
|---|---|---|---|---|
| W4-F1 | Candidate results reporting endpoints (filtering + pagination) | 16 | ❌ Not Started | [w4-f1-results-reporting-endpoints.md](features/w4-f1-results-reporting-endpoints.md) |
| W4-F2 | Candidate results page (Suspense, error boundaries, chart) | 17 | ❌ Not Started | [w4-f2-candidate-results-page.md](features/w4-f2-candidate-results-page.md) |
| W4-F3 | Role-based authz (API) + aggregate reporting queries | 18 | ❌ Not Started | [w4-f3-rbac-aggregate-queries.md](features/w4-f3-rbac-aggregate-queries.md) |
| W4-F4 | Trainer dashboard frontend (server RBAC, URL-synced filters) | 19 | ❌ Not Started | [w4-f4-trainer-dashboard-frontend.md](features/w4-f4-trainer-dashboard-frontend.md) |
| W4-F5 | Technical debt audit + ADR documentation | 20 | ❌ Not Started | [w4-f5-tech-debt-audit-adrs.md](features/w4-f5-tech-debt-audit-adrs.md) |

## Suggested order of attack

1. ~~**W2-F4 finish**~~ — done (PR #40).
2. ~~**W2-F5 pre-signed uploads**~~ — done (PR #49).
3. ~~**W2-F7 Alembic + Category**~~ — done (branch `richardh-feat-alembic`).
4. ~~**W2-F2 deepen**~~ — done (branch `richardh-feat-W2-F2`): multi-stage Dockerfiles + model/repo test depth + hermetic test DBs.
5. **W2-M10 reporting scaffold** — pairs naturally with W2-F7's Alembic work.
6. ~~**W2-F8 defect cleanup**~~ — done (PR #63: skills-500, user-service dual-engine, Pydantic-v2 sweep; gateway 204 was in W2-F7).
7. **W3-F1 sessions backend** — strict prerequisite for the whole Week 3 slice; lands as Alembic `0004` on W2-F7's chain.
8. **W3-F2 → W3-F3 → W3-F4** — the quiz-taking slice in dependency order; W3-F2 backend before the W3-F3/W3-F4 frontend that consumes it.
9. **W3-F5 + W3-F6** — verification layer; do last, once the endpoints + UI exist to test. (W3-F5 done — PR #79.)
9a. **W3-F7 review remediation before W3-F6** — fix the W3-F4 timer defect and settle active-session reuse semantics *before* the Playwright happy path freezes E2E behavior; the `/questions/sample` role gate previews W4-F3.
10. **W2-M10 (if not already) → W4-F1 → W4-F3** — reporting backend then its RBAC gate; both extend the scaffolded reporting service.
11. **W4-F2 → W4-F4** — results page first (builds `<ChartWrapper>`), then the trainer dashboard that reuses it; both need their W4 backends live.
12. **W4-F5 last** — debt audit + ADRs need a substantially complete codebase; capture the W4-F1 and W3-F2 ADR decisions as those features land.
