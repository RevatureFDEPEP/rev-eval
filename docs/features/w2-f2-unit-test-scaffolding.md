# W2-F2 — Unit Test Scaffolding (Frontend + Backend)

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §2 (Days 5 & 7)
**Unblocks:** W3-F2 (Scoring Engine — pytest must already be configured in test-management-service), W3-F5 (Integration Tests — builds on this scaffolding)
**Last updated:** 2026-06-09

Establish an automated unit testing foundation across the Next.js frontend and
Python backend services.

## Steps

- [x] **1. Frontend test scaffolding** — vitest + testing-library configured
      (`frontend/vitest.config.ts`, `pnpm test` = `vitest run`). Unit tests for
      question form utils (`frontend/src/components/trainer/question-form-utils`),
      commit `908dcb6`.
  - [x] Broaden coverage: presentation components, login layout, Zod client
        utility schemas. Added `frontend/vitest.setup.ts` (jest-dom matchers +
        afterEach cleanup, wired via `setupFiles`) and `@testing-library/react`
        tests for the quiz UI: `Timer` (formatting + warning/critical styling),
        `QuestionCard` (type dispatch + difficulty/number rendering),
        `MCQQuestion` and `MultiQuestion` (selection logic). Then closed the two
        spec-named gaps: `frontend/src/app/_components/landing-auth.test.tsx`
        (login layout — tab switch, login/register POST body, success
        navigation, error + network-error rendering, submit-disable) and
        `frontend/src/components/trainer/__tests__/question-schemas.test.ts`
        (dedicated Zod suite — `imageFileSchema` type/size, every
        `buildQuestionSchema` branch's refine rules, `baseSchema` field rules).
        70 frontend tests pass; `pnpm build` and `pnpm lint` stay green.
- [x] **2. Backend pytest scaffolding** — `tests/` in all 4 services
      (api-gateway-service, user-service, test-management-service,
      question-management-service), PR #32. Smoke tests: 5–8 per service.
  - [x] Deepen: parameterized unit tests targeting data models, repository CRUD
        functions, and Pydantic request validation schemas.
        - `test-management-service/tests/test_category_repository.py` — real
          `CategoryRepository` CRUD, link/unlink idempotency, eager skill load.
        - `question-management-service/tests/test_question_repository.py` —
          `QuestionRepository` CRUD, pagination, count, `find_by_*`, type-aware
          `QuestionCreate` validation.
        - `user-service/tests/test_user_model.py` — `User` persistence,
          unique-email constraint, role enum, schema validation.
        - `api-gateway-service/tests/test_routing.py` — full `ROUTES` table,
          `X-User-*` header injection, JWT auth boundary.
  - [x] Create dedicated test databases for repository-level tests — **hermetic
        in-memory**: aiosqlite `db_session` (test-management), mongomock-motor
        `beanie_db` (question-management), sync sqlite `db_session` (user). All
        backend tests pass with Postgres/Mongo down. Real Postgres/Mongo
        integration is owned by [W3-F5](w3-f5-integration-tests-real-db.md).
- [x] **3. Multi-stage Dockerfile test stages** — each backend Dockerfile is
      `base → test → production`. The `test` stage installs
      `requirements-dev.txt` and runs `pytest -q` (build fails if a test fails);
      the default build target stays `production`, so `docker compose up --build`
      is unchanged. CI now **runs** the stage: the backend matrix builds
      `docker build --target test` per service (step "Build & run container test
      stage" in `ci-pipeline.yml`) before the production build + Trivy scan, so
      container-level pytest gates the pipeline. `docker-compose.yml` is left on
      the `production` target — tests must not run on normal startup.

## Evidence

- New dev-deps manifests: `services/<svc>/requirements-dev.txt` (pytest,
  pytest-cov, ruff + per-service test-DB drivers). CI installs these instead of
  the old inline `pip install pytest pytest-cov ruff`.
- Coverage (Postgres/Mongo down): test-management 77.6%, question-management
  65.9%, user 68.1%, api-gateway 51.3% — each `.coveragerc` `fail_under` ratcheted
  to the new baseline (75 / 63 / 66 / 50).

## Notes

CI runs `pytest --cov` only when `services/<svc>/tests/` exists — all 4 now
qualify. Coverage *gating* belongs to [W2-F4](w2-f4-ci-quality-gates.md).
