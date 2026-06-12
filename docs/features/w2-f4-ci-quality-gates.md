# W2-F4 — CI Quality Gates (Ruff / ESLint / Trivy / Coverage)

**Status:** 🟡 In Progress
**Spec:** `days_6_10_features.md` §4 (Day 7) — priority REQUIRED
**Unblocks:** W3-F5 (Integration Tests — CI Postgres/Mongo service-container steps extend this pipeline structure)
**Last updated:** 2026-06-12

Extend `.github/workflows/ci-pipeline.yml` with static analysis and security
scanning quality gates — the intended completion of the seeded placeholder
comment ("Trivy + Ruff scans added in W2 D7 by candidates").

## Steps

- [x] **1. Ruff linting** — root `pyproject.toml` with Ruff config; `ruff
      check .` step in the backend matrix job after dependency install, before
      pytest (commit `6272053`). Ruff errors resolved across all backend
      services (`6507a63`, `f462bbf`, `21be2d9`).
- [x] **2. ESLint hard failure** — `|| echo` fallback removed from the
      frontend lint step; `pnpm lint` failures now block the build (commit
      `b1da154`). ESLint errors and warnings resolved (`2c35942`, `2df7178`).
      Also fixed the CI pnpm/lockfile mismatch: pinned `pnpm/action-setup@v4`
      to read the `packageManager` field (pnpm 9.15.0) (commit `895ccb4`).
- [ ] **3. Trivy container scan** — each backend matrix job should build its
      Docker image and scan with `aquasecurity/trivy-action`: severity
      CRITICAL/HIGH, `exit-code: 1`, `ignore-unfixed: true`. Not yet added to
      `ci-pipeline.yml`.
- [x] **4. pytest --cov** — backend matrix runs `pytest --cov --cov-report=xml`
      when a `tests/` directory is present ([W2-F2](w2-f2-unit-test-scaffolding.md)
      added tests to 3 services). Coverage XML uploaded as artifact.
      **Threshold enforcement not yet active** — `.coveragerc` files with
      `fail_under` do not exist; coverage runs but does not gate the build.

## Evidence

- Commits: `6272053` (Ruff in CI), `b1da154` (remove ESLint skip), `895ccb4`
  (pnpm v9 fix), `fd35635` (path-filtered CI runs).
- `ci-pipeline.yml`: `ruff check .` step in backend matrix; `pnpm lint` in
  frontend job; `pytest --cov --cov-report=xml` in backend matrix.
- Path filtering: jobs run only when relevant paths change (commit `fd35635`).

## Beyond spec

- Backend `actions/checkout` bumped v3 → v4 to match the frontend job.
- Removed `actions/attest-build-provenance` which caused workflow failures
  (commit `c1c062c`).

## Remaining

- **Trivy container scan** — add `aquasecurity/trivy-action` step to each
  backend matrix job (CRITICAL/HIGH, `exit-code: 1`, `ignore-unfixed: true`),
  upload SARIF per service.
- **Coverage fail-under thresholds** — create per-service `.coveragerc` with
  `fail_under` ratcheted to measured baselines (e.g. 75 / 63 / 66 for
  test-management / question-management / user).
