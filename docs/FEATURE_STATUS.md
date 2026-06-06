# Feature Status Tracker

Summary of implementation state for the candidate features defined in the
curriculum spec files (`days_*_features.md` at the workspace root, one level
above this repo). Currently covers **Days 6–10**; add rows and feature files as
Week 3 / 4 specs are picked up.

Each feature has a detail file under [`docs/features/`](features/) with a
step-wise checklist, evidence (file paths, PRs, commits), and remaining work.
This file stays at summary level only.

> **Workflow:** this tracker is part of the feature delivery loop. When you
> start, advance, or finish a feature, update its detail file (check off steps,
> add evidence) **and** its status row here, in the same PR as the code change.

**Last assessed:** 2026-06-05 (branch `richardh-feat-alembic`)

## Status values

| Status | Meaning |
|---|---|
| ✅ Completed | All spec acceptance criteria met |
| 🟡 In Progress | Some steps done; open items listed in the detail file |
| ❌ Not Started | No meaningful implementation in the repo |

## Days 6–10

| # | Feature | Spec priority | Status | Detail |
|---|---|---|---|---|
| F1 | Nginx path-based routing & local TLS | REQUIRED | ✅ Completed | [f1-nginx-routing-tls.md](features/f1-nginx-routing-tls.md) |
| F2 | Unit test scaffolding (frontend + backend) | — | 🟡 In Progress | [f2-unit-test-scaffolding.md](features/f2-unit-test-scaffolding.md) |
| F3 | Centralized log aggregation (Loki/Grafana) | — | ✅ Completed | [f3-log-aggregation.md](features/f3-log-aggregation.md) |
| F4 | CI quality gates (Ruff / ESLint / Trivy / coverage) | REQUIRED | ✅ Completed | [f4-ci-quality-gates.md](features/f4-ci-quality-gates.md) |
| F5 | Direct-to-MinIO diagram uploads (pre-signed URLs) | — | ✅ Completed | [f5-minio-presigned-uploads.md](features/f5-minio-presigned-uploads.md) |
| F6 | Structured question authoring interface | — | ✅ Completed | [f6-question-authoring-ui.md](features/f6-question-authoring-ui.md) |
| F7 | Alembic migrations & Category domain | — | ✅ Completed | [f7-alembic-category-domain.md](features/f7-alembic-category-domain.md) |
| F8 | Pre-existing defect cleanup (found during F7) | — | 🟡 In Progress | [f8-pre-existing-defects.md](features/f8-pre-existing-defects.md) |
| M10 | Day 10 milestone: reporting service scaffold | milestone | ❌ Not Started | [m10-reporting-service-scaffold.md](features/m10-reporting-service-scaffold.md) |

## Suggested order of attack

1. ~~**F4 finish**~~ — done (PR #40).
2. ~~**F5 pre-signed uploads**~~ — done (PR #49).
3. ~~**F7 Alembic + Category**~~ — done (branch `richardh-feat-alembic`).
4. **F2 deepen** — multi-stage Dockerfiles + model/repo test depth.
5. **M10 reporting scaffold** — pairs naturally with F7's Alembic work.
6. **F8 defect cleanup** — small fixes, good filler tasks between features (gateway 204 item already done in F7).
