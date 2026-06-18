# docs/ Index

Quick-reference for Claude Code. Given a feature ID (e.g. `w2-f1`), this file
tells you every relevant document to read.

---

## Document Types

| Directory / File                       | What it contains                                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `FEATURE_STATUS.md`                    | Live status table for all features + suggested order of attack. Read first.                                |
| `features/{id}.md`                     | Step checklist, evidence (commits/PRs/branches), remaining work. Source of truth for implementation state. |
| `feature_specs/{id}.md`                | Curriculum fit, prerequisites, cross-week dependencies, implementation details (what to build).            |
| `feature_specs/days_6_10_features.md`  | Combined original spec — W2 features (Days 6–10).                                                          |
| `feature_specs/days_11_15_features.md` | Combined original spec — W3 features (Days 11–15).                                                         |
| `feature_specs/days_16_20_features.md` | Combined original spec — W4 features (Days 16–20).                                                         |
| `plans/{id}-plan.md`                   | Code-level implementation plan: file paths, code snippets, step-by-step. Exists only for some features.    |

---

## Feature Lookup

### Week 2 — Days 6–10 (platform hardening & question bank)

| ID     | Title                                               | Status         | `features/`                                                                            | `feature_specs/`                                                                                         | `plans/` |
| ------ | --------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------- |
| W2-F1  | Nginx path-based routing & local TLS                | ✅ Completed   | [features/w2-f1-nginx-routing-tls.md](features/w2-f1-nginx-routing-tls.md)             | [feature_specs/w2-f1-nginx-routing-tls.md](feature_specs/w2-f1-nginx-routing-tls.md)                     | —        |
| W2-F2  | Unit test scaffolding (frontend + backend)          | 🟡 In Progress | [features/w2-f2-unit-test-scaffolding.md](features/w2-f2-unit-test-scaffolding.md)     | [feature_specs/w2-f2-unit-test-scaffolding.md](feature_specs/w2-f2-unit-test-scaffolding.md)             | —        |
| W2-F3  | Centralized log aggregation (Loki/Grafana)          | ❌ Not Started | [features/w2-f3-log-aggregation.md](features/w2-f3-log-aggregation.md)                 | [feature_specs/w2-f3-log-aggregation.md](feature_specs/w2-f3-log-aggregation.md)                         | —        |
| W2-F4  | CI quality gates (Ruff / ESLint / Trivy / coverage) | 🟡 In Progress | [features/w2-f4-ci-quality-gates.md](features/w2-f4-ci-quality-gates.md)               | [feature_specs/w2-f4-ci-quality-gates.md](feature_specs/w2-f4-ci-quality-gates.md)                       | —        |
| W2-F5  | Direct-to-MinIO diagram uploads (pre-signed URLs)   | ❌ Not Started | [features/w2-f5-minio-presigned-uploads.md](features/w2-f5-minio-presigned-uploads.md) | [feature_specs/w2-f5-minio-presigned-uploads.md](feature_specs/w2-f5-minio-presigned-uploads.md)         | —        |
| W2-F6  | Structured question authoring interface             | 🟡 In Progress | [features/w2-f6-question-authoring-ui.md](features/w2-f6-question-authoring-ui.md)     | [feature_specs/w2-f6-question-authoring-ui.md](feature_specs/w2-f6-question-authoring-ui.md)             | —        |
| W2-F7  | Alembic migrations & Category domain                | ✅ Completed   | [features/w2-f7-alembic-category-domain.md](features/w2-f7-alembic-category-domain.md) | [feature_specs/w2-f7-alembic-category-domain.md](feature_specs/w2-f7-alembic-category-domain.md)         | —        |

### Week 3 — Days 11–15 (quiz-taking vertical slice)

| ID    | Title                                                | Status         | `features/`                                                                                        | `feature_specs/`                                                                                             | `plans/`                                                                             |
| ----- | ---------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| W3-F1 | Quiz session creation backend (`POST /sessions`)     | ✅ Completed   | [features/w3-f1-quiz-session-backend.md](features/w3-f1-quiz-session-backend.md)                   | [feature_specs/w3-f1-quiz-session-backend.md](feature_specs/w3-f1-quiz-session-backend.md)                   | [plans/w3-f1-quiz-session-backend-plan.md](plans/w3-f1-quiz-session-backend-plan.md) |
| W3-F2 | Scoring engine + pessimistic locking                 | ✅ Completed   | [features/w3-f2-scoring-engine-locking.md](features/w3-f2-scoring-engine-locking.md)               | [feature_specs/w3-f2-scoring-engine-locking.md](feature_specs/w3-f2-scoring-engine-locking.md)               | [plans/w3-f2-scoring-engine-plan.md](plans/w3-f2-scoring-engine-plan.md)             |
| W3-F3 | Test-taking frontend skeleton (`/take/[testId]`)     | ✅ Completed   | [features/w3-f3-test-taking-frontend-skeleton.md](features/w3-f3-test-taking-frontend-skeleton.md) | [feature_specs/w3-f3-test-taking-frontend-skeleton.md](feature_specs/w3-f3-test-taking-frontend-skeleton.md) | [plans/w3-f3-test-taking-frontend-skeleton-plan.md](plans/w3-f3-test-taking-frontend-skeleton-plan.md) |
| W3-F4 | Auto-saving exam client (server timer + submit-lock) | ❌ Not Started | [features/w3-f4-autosave-exam-client.md](features/w3-f4-autosave-exam-client.md)                   | [feature_specs/w3-f4-autosave-exam-client.md](feature_specs/w3-f4-autosave-exam-client.md)                   | —                                                                                    |
| W3-F5 | Integration tests vs. real Postgres/Mongo            | ❌ Not Started | [features/w3-f5-integration-tests-real-db.md](features/w3-f5-integration-tests-real-db.md)         | [feature_specs/w3-f5-integration-tests-real-db.md](feature_specs/w3-f5-integration-tests-real-db.md)         | —                                                                                    |
| W3-F6 | Playwright E2E happy path + smoke script             | ❌ Not Started | [features/w3-f6-playwright-e2e-smoke.md](features/w3-f6-playwright-e2e-smoke.md)                   | [feature_specs/w3-f6-playwright-e2e-smoke.md](feature_specs/w3-f6-playwright-e2e-smoke.md)                   | —                                                                                    |
| W3-F7 | Week-3 review-findings remediation (non-catalog)     | ❌ Not Started | [features/w3-f7-review-remediation.md](features/w3-f7-review-remediation.md)                       | _(not yet created)_                                                                                          | —                                                                                    |

### Week 4 — Days 16–20 (reporting, RBAC & trainer dashboard)

| ID    | Title                                                        | Status         | `features/`                                                                                    | `feature_specs/`                                                                                         | `plans/` |
| ----- | ------------------------------------------------------------ | -------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------- |
| W4-F1 | Candidate results reporting endpoints                        | ✅ Completed   | [features/w4-f1-results-reporting-endpoints.md](features/w4-f1-results-reporting-endpoints.md) | [feature_specs/w4-f1-results-reporting-endpoints.md](feature_specs/w4-f1-results-reporting-endpoints.md) | [plans/w4-f1-results-reporting-endpoints-plan.md](plans/w4-f1-results-reporting-endpoints-plan.md) |
| W4-F2 | Candidate results page (Suspense, error boundaries, chart)   | ❌ Not Started | [features/w4-f2-candidate-results-page.md](features/w4-f2-candidate-results-page.md)           | [feature_specs/w4-f2-candidate-results-page.md](feature_specs/w4-f2-candidate-results-page.md)           | —        |
| W4-F3 | Role-based authz (API) + aggregate reporting queries         | ❌ Not Started | [features/w4-f3-rbac-aggregate-queries.md](features/w4-f3-rbac-aggregate-queries.md)           | [feature_specs/w4-f3-rbac-aggregate-queries.md](feature_specs/w4-f3-rbac-aggregate-queries.md)           | —        |
| W4-F4 | Trainer dashboard frontend (server RBAC, URL-synced filters) | ❌ Not Started | [features/w4-f4-trainer-dashboard-frontend.md](features/w4-f4-trainer-dashboard-frontend.md)   | [feature_specs/w4-f4-trainer-dashboard-frontend.md](feature_specs/w4-f4-trainer-dashboard-frontend.md)   | —        |
| W4-F5 | Technical debt audit + ADR documentation                     | ❌ Not Started | [features/w4-f5-tech-debt-audit-adrs.md](features/w4-f5-tech-debt-audit-adrs.md)               | [feature_specs/w4-f5-tech-debt-audit-adrs.md](feature_specs/w4-f5-tech-debt-audit-adrs.md)               | —        |

---

## Reading Order for Any Feature

1. **This index** — confirm which docs exist for the ID.
2. **`FEATURE_STATUS.md`** — current status and any open notes.
3. **`features/{id}.md`** — step checklist + evidence (what's done, what's left).
4. **`feature_specs/{id}.md`** — what to build (implementation details, prereqs, cross-week deps).
5. **`plans/{id}-plan.md`** — code-level plan if it exists (file paths, code snippets).
6. **`feature_specs/days_*_features.md`** — original combined spec if deeper context needed.

---

## Dependency Graph (abbreviated)

```
W2-F7 ──► W3-F1 ──► W3-F2 ──► W3-F4 ──► W3-F6
           │          │
           └──► W3-F3─┘──► W4-F2
W2-F5 ──► W2-F6        W3-F2 ──► W4-F1 ──► W4-F3 ──► W4-F4
W2-F4 ──► W3-F5                  W4-F1 ──► W4-F5
W2-F1 ──► W3-F3, W3-F6, W4-F2, W4-F4
```

Full dependency details are in each `feature_specs/{id}.md` under
**Cross-Week Dependencies** and **Required for**.

---

## Missing Files (linked from FEATURE_STATUS.md but not yet created)

| File                                        | Needed for  |
| ------------------------------------------- | ----------- |
| `feature_specs/w3-f7-review-remediation.md` | W3-F7 spec  |
