# F2 — Unit Test Scaffolding (Frontend + Backend)

**Status:** 🟡 In Progress
**Spec:** `days_6_10_features.md` §2 (Days 5 & 7)
**Unblocks:** W3-F2 (Scoring Engine — pytest must already be configured in test-management-service), W3-F5 (Integration Tests — builds on this scaffolding)
**Last updated:** 2026-06-04

Establish an automated unit testing foundation across the Next.js frontend and
Python backend services.

## Steps

- [x] **1. Frontend test scaffolding** — vitest + testing-library configured
      (`frontend/vitest.config.ts`, `pnpm test` = `vitest run`). Unit tests for
      question form utils (`frontend/src/components/trainer/question-form-utils`),
      commit `908dcb6`.
  - [ ] Broaden coverage: presentation components, login layouts, Zod client
        utility schemas (currently 1 test file).
- [x] **2. Backend pytest scaffolding** — `tests/` in all 4 services
      (api-gateway-service, user-service, test-management-service,
      question-management-service), PR #32. Smoke tests: 5–8 per service.
  - [ ] Deepen: parameterized unit tests targeting data models, repository CRUD
        functions, and Pydantic request validation schemas (currently 1
        smoke-test file per service).
  - [ ] Create dedicated test databases for repository-level tests.
- [ ] **3. Multi-stage Dockerfile test stages** — none exist. Add a test stage
      per service Dockerfile that installs dev dependencies and runs pytest
      before the production image layer is assembled, so CI can run tests
      inside the container.

## Remaining

- Multi-stage Dockerfile test stages (step 3) — not started.
- Test depth on both frontend and backend (sub-items under steps 1–2).

## Notes

CI runs `pytest --cov` only when `services/<svc>/tests/` exists — all 4 now
qualify. Coverage *gating* belongs to [F4](f4-ci-quality-gates.md).
