# F4 — CI Quality Gates (Ruff / ESLint / Trivy / Coverage)

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §4 (Day 7) — priority REQUIRED
**Unblocks:** W3-F5 (Integration Tests — CI Postgres/Mongo service-container steps extend this pipeline structure)
**Last updated:** 2026-06-04 (PR #40 merged)

Extend `.github/workflows/ci-pipeline.yml` with static analysis and security
scanning quality gates — the intended completion of the seeded placeholder
comment ("Trivy + Ruff scans added in W2 D7 by candidates").

## Steps

- [x] **1. Ruff linting** — root `pyproject.toml` with Ruff config; `ruff
      check .` step in the backend matrix job after dependency install, before
      pytest (PR #28). Line length kept at 120 (not spec's 88) — rationale
      documented in `pyproject.toml`.
- [x] **2. ESLint hard failure** — `|| echo` fallback removed; `pnpm lint`
      failures now block the build (PR #40, `b13b928`). Also fixed the CI
      pnpm/lockfile mismatch this exposed: the job pinned pnpm 8, which cannot
      read the v9 lockfile, so CI silently re-resolved deps and linted with
      different plugin versions than local dev. Now `pnpm/action-setup@v4`
      reads the `packageManager` field (pnpm 9.15.0) (`8e5241b`).
- [x] **3. Trivy container scan** — each backend matrix job builds its Docker
      image and scans it with `aquasecurity/trivy-action@v0.36.0`: severity
      CRITICAL/HIGH, `exit-code: 1`, `ignore-unfixed: true` (so unpatchable
      base-image CVEs don't dead-lock the pipeline), SARIF uploaded as a
      per-service artifact with `if: always()` (PR #40, `1dbbc37`, `0d550e2`).
- [x] **4. Coverage threshold** — per-service `.coveragerc` (source/omit +
      `fail_under`) as a measured-baseline ratchet instead of the spec's
      aspirational 70 (smoke tests only; cohort decision):
      api-gateway 47%→45, user 60%→58, question-mgmt 50%→48,
      test-mgmt 45%→43. `coverage.xml` uploaded as per-service artifact
      (PR #40, `7251a55`). Raise thresholds as test depth grows (F2).

## Evidence

- PR [#40](https://github.com/RevatureFDEPEP/rev-eval/pull/40) — merged
  2026-06-04, all checks green (4 backend matrix jobs + frontend).
- Plan: [`docs/plans/ci-quality-gates.md`](../plans/ci-quality-gates.md).
- Gate proven live: first Trivy run failed on real fixable HIGH CVEs shipped
  in `python:3.11-slim` tooling (`jaraco.context` 5.3.0 CVE-2026-23949,
  `wheel` 0.45.1 CVE-2026-24049); fixed by upgrading
  pip/setuptools/wheel/jaraco.context in all 4 Dockerfiles before
  `pip install -r requirements.txt` (`88debe5`), verified clean locally with
  the same Trivy flags as CI.

## Beyond spec

- Path filtering: jobs run only for changed paths (commit `52000ea`).
- Backend `actions/checkout` bumped v3 → v4 to match the rest of the workflow.
- Dockerfile base-image tooling CVE remediation (above) — spec only asked for
  the scan; the scan's findings were fixed too.

## Remaining

- Nothing for the spec. Follow-ups live elsewhere: raise coverage ratchets as
  F2 adds tests; W3-F5 extends this job structure with service containers.
