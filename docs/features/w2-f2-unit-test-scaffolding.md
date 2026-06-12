# W2-F2 — Unit Test Scaffolding (Frontend + Backend)

**Status:** 🟡 In Progress
**Spec:** `days_6_10_features.md` §2 (Days 5 & 7)
**Unblocks:** W3-F2 (Scoring Engine — pytest must already be configured in test-management-service), W3-F5 (Integration Tests — builds on this scaffolding)
**Last updated:** 2026-06-12

Establish an automated unit testing foundation across the Next.js frontend and
Python backend services.

## Steps

- [x] **1. Frontend test scaffolding** — Jest 30 + `@testing-library/react` 16
      configured (`frontend/jest.config.js`, `frontend/jest.setup.ts`;
      `pnpm test` = `jest`). 102 tests across lib utilities, Zod schemas, and
      presentation components (commit `e9c179a`):
  - `src/__tests__/lib/utils.test.ts`, `src/__tests__/lib/date.test.ts` — `cn()` and date utils.
  - `src/__tests__/lib/schemas/auth.test.ts`, `question-form.test.ts`,
    `test-form.test.ts` — Zod schema validation for login/register, question
    form types, and test creation rules.
  - `src/__tests__/components/LandingAuth.test.tsx` — login layout: tab switch,
    POST body, success navigation, error + network-error, submit-disable.
  - `src/__tests__/components/quiz/MCQQuestion.test.tsx`,
    `ProgressHeader.test.tsx`, `TrueFalseQuestion.test.tsx` — quiz UI
    interaction and rendering.
- [x] **2. Backend pytest scaffolding** — `tests/` in three services with
      hermetic in-memory fixtures; `requirements-test.txt` + `pytest.ini` per
      service (commit `b7b6506`; CI fix `b9df25b`, lint fix `e6e6287`):
  - `test-management-service` (121 tests) — aiosqlite in-memory async DB;
    `test_models.py`, `test_schemas.py`, `test_skill_repository.py`,
    `test_submission_repository.py`, `test_test_repository.py`.
  - `user-service` (83 tests) — sync SQLite in-memory; `test_models.py`,
    `test_schemas.py`, `test_auth_service.py`.
  - `question-management-service` — mongomock-motor in-memory Beanie DB;
    `test_models.py`, `test_schemas.py`, `test_repository.py`.
  - `api-gateway-service` — no `tests/` directory; not yet scaffolded.
  - All backend tests pass with Postgres/Mongo down. Real DB integration owned
    by [W3-F5](w3-f5-integration-tests-real-db.md).
- [ ] **3. Multi-stage Dockerfile test stages** — add `base → test → production`
      stages to all 4 backend Dockerfiles so `docker build --target test` runs
      `pytest -q` and gates the CI pipeline at the container level. Current
      Dockerfiles are single-stage (`FROM python:3.11-slim`).

## Evidence

- Frontend: `frontend/jest.config.js`, `frontend/jest.setup.ts`, 9 test files
  under `frontend/src/__tests__/`.
- Backend: `tests/` + `requirements-test.txt` + `pytest.ini` in
  `test-management-service`, `user-service`, `question-management-service`.
- CI (`ci-pipeline.yml`): backend matrix installs `requirements-test.txt` when
  present and runs `pytest --cov --cov-report=xml`. Coverage reports generated
  but **no `fail_under` threshold enforced** — `.coveragerc` files do not exist;
  threshold gating is tracked under [W2-F4](w2-f4-ci-quality-gates.md).

## Notes

`pnpm test --if-present` in the frontend CI job picks up Jest automatically.
Coverage *gating* (fail-under thresholds) belongs to [W2-F4](w2-f4-ci-quality-gates.md).
