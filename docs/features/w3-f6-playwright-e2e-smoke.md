# W3-F6 — Playwright End-to-End Happy Path + Smoke Script

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §6 (Day 15)
**Depends on:** [W2-F1](w2-f1-nginx-routing-tls.md) (Playwright navigates through port 80/443 as a browser; single entry point must be wired), W3-F3 + W3-F4 (full quiz UI incl. timer + submit-lock must exist for the happy path), W3-F5 (smoke-script pattern reused as pre-flight health check)
**Last updated:** 2026-06-12

Playwright E2E test covering the happy-path login → take quiz → submit → results
flow, plus a standalone smoke script for pre-flight health checks.

## Steps

- [ ] **1. Install Playwright** — `@playwright/test` in the frontend
      `devDependencies`; `playwright.config.ts` targeting `https://localhost`.
- [ ] **2. Happy-path spec** — `e2e/quiz-happy-path.spec.ts`: login →
      navigate to test → answer all questions → submit → assert results page.
- [ ] **3. Smoke script** — standalone `scripts/smoke.ts` (no browser) that
      hits health endpoints on all services; exit 1 if any unhealthy.
- [ ] **4. CI job** — `e2e` job in `ci-pipeline.yml`: `docker compose up`,
      wait for healthy, run `playwright test`.
- [ ] **5. Log artifact** — upload Playwright HTML report on failure.

## Evidence

None on `tianyac` branch. No `playwright.config.ts`, no `e2e/` directory.

Note: another contributor delivered this feature on branch
`richardh-feat-W3F6`; that work is not yet merged into `tianyac`.

## Remaining

All steps. Blocked on [W3-F3](w3-f3-test-taking-frontend-skeleton.md) and
[W3-F4](w3-f4-autosave-exam-client.md).
