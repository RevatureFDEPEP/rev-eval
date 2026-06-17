# W2-F4 — Ruff Linting, ESLint, and Trivy Container Scanning in CI

*Extend the existing CI pipeline with static analysis and security scanning quality gates, completing the Day 7 candidate tasks called out in the pipeline comment.*

* **Curriculum Fit**: Day 7 (Code quality linting with Ruff and ESLint, container scanning with Trivy, test coverage reporting and quality gates, CI pipeline optimization).
* **Prerequisites**: Day 7 topics.
* **Status**: REQUIRED — Establishes the CI quality gates and service-container job patterns that Week 3 integration testing directly extends. Completing this before W3 prevents having to restructure the pipeline mid-week.
* **Required for**: W3-F5 (Integration Tests Against Real Postgres and Mongo Containers — CI Postgres/Mongo service-container steps extend this pipeline structure)
* **Time Estimate**: Without AI tools: 3–5 hours | With AI tools (Gemini/Claude Code): 1–2 hours
* **Note**: The `ci-pipeline.yml` already contains the comment `# NOTE: Trivy + Ruff scans added in W2 D7 by candidates (not seeded here)` — this feature is the intended completion of that placeholder.

## Implementation Details

1. Add a `pyproject.toml` at the repo root (or per-service) configuring Ruff with `target-version = "py311"`, a line length of 88, and a rule set covering pyflakes (F), pycodestyle (E/W), isort (I), and the bugbear (B) rules. Add `ruff check .` as a CI step in the backend matrix job, after dependency installation and before pytest.
2. Verify that the frontend lint step (`pnpm lint`) runs ESLint with a config that enforces the Next.js recommended rule set. Restore the step in `ci-pipeline.yml` to a hard failure (remove the `|| fallback` added recently) so linting failures block the build rather than being silently skipped.
3. Add a Trivy scan step to the backend matrix job using the `aquasecurity/trivy-action` GitHub Action. Configure it to scan the built Docker image, set `exit-code: 1` so CRITICAL and HIGH CVEs fail the pipeline, and upload the SARIF report as a CI artifact for review.
4. Add a coverage threshold to the pytest step: use `--cov-fail-under=70` (or the threshold agreed with the cohort) so a drop in test coverage fails the build. Upload the coverage XML as a CI artifact so trends are visible across runs.
