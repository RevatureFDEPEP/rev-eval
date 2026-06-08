# W2-F4 — CI Quality Gates (Ruff / ESLint / Trivy / Coverage)

## Context

W2-D7 feature from `days_6_10_features.md` §4 — extend `.github/workflows/ci-pipeline.yml` with quality gates. Status REQUIRED (W3-F5 integration tests build on this pipeline structure).

Spec has 4 items; current state:

1. **Ruff** — DONE. Root `pyproject.toml` config + `ruff check .` step at `ci-pipeline.yml:98-100`. Decision: keep line-length 120 (not spec's 88) — already justified in pyproject comment.
2. **ESLint hard fail** — TODO. `ci-pipeline.yml:141` is `pnpm lint || echo "Linting failed, attempting build anyway."` — failures silently skipped.
3. **Trivy image scan** — TODO. Placeholder comment at `ci-pipeline.yml:111`. Backend matrix job never builds Docker images.
4. **Coverage threshold + artifact** — TODO. All 4 services have `tests/test_smoke.py` only; no coverage config or threshold.

Decisions:
- Coverage: **measured-baseline ratchet** — measure actual per-service coverage during implementation, set `fail_under` just below it per service (gate = no regression, not aspirational 70).
- Trivy: **`ignore-unfixed: true`** — fail only on fixable CRITICAL/HIGH (base `python:3.11-slim` ships unfixable HIGHs that would dead-lock CI).
- Ruff: **keep 120**, no change to pyproject.

## Changes

### 1. `frontend/` lint hard fail — `.github/workflows/ci-pipeline.yml:139-141`

```yaml
      - name: Lint
        working-directory: frontend
        run: pnpm lint
```

Pre-check: run `pnpm lint` locally first; if it currently fails, fix the lint errors in the same branch (otherwise this change reds the pipeline immediately).

### 2. Coverage gate — per-service `.coveragerc` (×4) + pipeline step

New file `services/<svc>/.coveragerc` for each of `api-gateway-service`, `user-service`, `question-management-service`, `test-management-service`:

```ini
[run]
# api-gateway-service: code lives in main.py (no src/); use the right source per service
source = src        # or `.` with omit for the gateway
omit =
    tests/*
    seed_*.py

[report]
fail_under = <NN>   # measured baseline minus ~2pts, per service
```

Measurement procedure (during implementation, per service):
```bash
cd services/<svc>
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest pytest-cov
.venv/bin/pytest --cov --cov-report=term --cov-report=xml
```
Set each `fail_under` ≈ 2 points below measured. pytest-cov honors `.coveragerc` automatically, so CI step stays uniform across the matrix.

Pipeline pytest step (`ci-pipeline.yml:102-109`) gains XML artifact upload after it:

```yaml
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-${{ matrix.service }}
          path: services/${{ matrix.service }}/coverage.xml
          if-no-files-found: ignore
```

(`--cov --cov-report=xml` already in the existing step; threshold enforced via `.coveragerc` `fail_under`.)

### 3. Trivy scan — backend matrix job, after pytest (replaces comment at line 111)

```yaml
      - name: Build Docker image
        working-directory: services/${{ matrix.service }}
        run: docker build -t ${{ matrix.service }}:${{ github.sha }} .

      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ matrix.service }}:${{ github.sha }}
          format: sarif
          output: trivy-${{ matrix.service }}.sarif
          severity: CRITICAL,HIGH
          exit-code: '1'
          ignore-unfixed: true

      - name: Upload Trivy SARIF
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: trivy-${{ matrix.service }}
          path: trivy-${{ matrix.service }}.sarif
          if-no-files-found: ignore
```

Notes:
- `if: always()` on uploads — Trivy writes SARIF before exiting 1, so the report survives a failing gate.
- Spec says "upload SARIF as a CI artifact" → `actions/upload-artifact`, not the code-scanning API (Advanced Security not assumed).
- Frontend image not scanned — spec scopes Trivy to the backend matrix job.

### 4. Housekeeping in same edit

- Bump backend job `actions/checkout@v3` → `@v4` (line 74; rest of file already on v4).
- Update/remove the stale `# NOTE: Trivy container scan still pending` comment (line 111).
- `paths-filter` already routes root `pyproject.toml` → all backends and per-service files → that service's job; new `.coveragerc` files live inside service dirs so no filter change needed.

## Branch & commits

Work on branch **`richardh-feat-linting`** (off `richardh`). Commit at each milestone:

1. `docs: add CI quality gates implementation plan`
2. `ci(frontend): make pnpm lint a hard failure` (+ any `fix(frontend): ...` lint fixes as separate commit)
3. `ci: enforce per-service coverage thresholds`
4. `ci: add Trivy image scan with SARIF artifact`

## Files

| File | Change |
|---|---|
| `.github/workflows/ci-pipeline.yml` | lint hard fail; coverage artifact upload; docker build + Trivy + SARIF upload; checkout v4 |
| `services/{api-gateway,user,question-management,test-management}-service/.coveragerc` | new — source/omit + measured `fail_under` |
| `frontend/**` | only if `pnpm lint` currently fails — fix errors |
| `docs/plans/w2-f4-ci-quality-gates.md` | new — this plan |

No change: `pyproject.toml` (Ruff stays as-is), eslint.config.mjs (already Next recommended rule set).

## Verification

1. **Ruff**: `cd services/<svc> && ruff check .` ×4 — confirm clean.
2. **ESLint**: `cd frontend && pnpm lint` — must exit 0.
3. **Coverage**: per-service venv pytest run (procedure above) — confirm each passes its new `fail_under` and fails when threshold artificially raised (spot-check one).
4. **Trivy locally** (if trivy CLI present): `docker build -t user-service:test services/user-service && trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 user-service:test`; else rely on CI.
5. **Workflow syntax**: `actionlint .github/workflows/ci-pipeline.yml` if available.
6. **End-to-end**: push branch, open PR (or `workflow_dispatch`) — confirm all 4 backend matrix jobs + frontend job green, coverage + SARIF artifacts attached to the run.
