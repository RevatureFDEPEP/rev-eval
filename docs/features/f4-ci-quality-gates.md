# F4 — CI Quality Gates (Ruff / ESLint / Trivy / Coverage)

**Status:** 🟡 In Progress
**Spec:** `days_6_10_features.md` §4 (Day 7) — priority REQUIRED
**Unblocks:** W3-F5 (Integration Tests — CI Postgres/Mongo service-container steps extend this pipeline structure)
**Last updated:** 2026-06-04

Extend `.github/workflows/ci-pipeline.yml` with static analysis and security
scanning quality gates — the intended completion of the seeded placeholder
comment ("Trivy + Ruff scans added in W2 D7 by candidates").

## Steps

- [x] **1. Ruff linting** — root `pyproject.toml` with Ruff config; `ruff
      check .` step in the backend matrix job after dependency install, before
      pytest (PR #28).
- [ ] **2. ESLint hard failure** — frontend lint step currently soft-fails:
      `pnpm lint || echo "Linting failed, attempting build anyway."`
      (ci-pipeline.yml:141). Remove the `||` fallback so lint failures block
      the build.
- [ ] **3. Trivy container scan** — not started; pipeline comment confirms
      (ci-pipeline.yml:111 "Trivy container scan still pending (W2 D7)"). Add
      `aquasecurity/trivy-action` scanning the built image, `exit-code: 1` on
      CRITICAL/HIGH CVEs, upload SARIF report as CI artifact.
- [ ] **4. Coverage threshold** — `pytest --cov --cov-report=xml` runs
      (ci-pipeline.yml:106) but nothing gates. Add `--cov-fail-under=70` (or
      cohort-agreed threshold) and upload coverage XML as CI artifact.

## Beyond spec

- Path filtering: jobs run only for changed paths (commit `52000ea`).

## Remaining

- Steps 2–4 above.
