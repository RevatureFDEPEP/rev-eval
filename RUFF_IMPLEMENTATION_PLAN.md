# Ruff Linting Implementation Plan

## Overview

Add [Ruff](https://docs.astral.sh/ruff/) as the project-wide Python linter for all four backend services. The CI pipeline already has a placeholder comment for this (`# NOTE: Trivy + Ruff scans added in W2 D7 by candidates`), so this is a planned addition.

**Scope:** `services/api-gateway-service`, `services/user-service`, `services/test-management-service`, `services/question-management-service`

---

## Step 1 — Add `pyproject.toml` at the repo root

Create a single `pyproject.toml` at the project root to centralize Ruff configuration for all services. Ruff walks up the directory tree to find this file, so one config covers every service.

```toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes (undefined names, unused imports)
    "I",   # isort (import ordering)
    "B",   # flake8-bugbear (common bugs)
    "UP",  # pyupgrade (modernize syntax)
]
ignore = [
    "E501",  # line too long — handled by formatter, not linter
]

[tool.ruff.lint.isort]
known-first-party = [
    "config",
    "db",
    "models",
    "schemas",
    "repositories",
    "services",
    "v1",
    "utils",
]
```

> **Why a root `pyproject.toml`?** A single config keeps rules consistent across all services and avoids duplicating settings in five separate files.

---

## Step 2 — Add Ruff to each service's `requirements.txt`

Add `ruff` as a dev dependency in each service so it's available locally and in CI when dependencies are installed.

**Files to update:**
- `services/api-gateway-service/requirements.txt`
- `services/user-service/requirements.txt`
- `services/test-management-service/requirements.txt`
- `services/question-management-service/requirements.txt`

**Line to append to each:**
```
ruff
```

> Alternatively, create a shared `requirements-dev.txt` at the repo root and install it alongside each service's requirements in CI. Either approach works; per-service is simpler.

---

## Step 3 — Run Ruff locally to assess baseline violations

Before wiring up CI, run Ruff against each service to see the current violation count and fix auto-fixable issues.

```bash
# From the repo root — check all services
ruff check services/

# Auto-fix safe violations (unused imports, isort, pyupgrade, etc.)
ruff check services/ --fix

# Format code (optional but recommended)
ruff format services/
```

Review the remaining violations manually and decide whether to fix them before or alongside the CI step.

---

## Step 4 — Update the CI pipeline

Add a Ruff lint step to `.github/workflows/ci-pipeline.yml` inside the `backend-build-test` job, **after** `Install dependencies` and **before** `Run pytest`.

```yaml
- name: Lint with Ruff
  working-directory: services/${{ matrix.service }}
  run: ruff check . --output-format=github
```

`--output-format=github` emits annotations directly in the GitHub PR diff view.

**Updated job step order:**
1. Checkout
2. Set up Python
3. Verify JWT_SECRET
4. Install dependencies ← `ruff` is now installed here
5. **Lint with Ruff** ← new step
6. Run pytest

---

## Step 5 — (Optional) Add a pre-commit hook

For local enforcement before commits, add a `.pre-commit-config.yaml` at the repo root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0   # pin to a stable version
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Install once per developer machine:
```bash
pip install pre-commit
pre-commit install
```

---

## Summary Checklist

- [ ] Create `pyproject.toml` at repo root with Ruff config
- [ ] Append `ruff` to each service's `requirements.txt`
- [ ] Run `ruff check services/ --fix` locally, review and commit fixes
- [ ] Add `Lint with Ruff` step to `ci-pipeline.yml`
- [ ] (Optional) Add `.pre-commit-config.yaml` for local enforcement
- [ ] Open PR, confirm CI passes with Ruff step green
