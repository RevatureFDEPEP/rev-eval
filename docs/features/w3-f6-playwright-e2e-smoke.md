# W3-F6 — Playwright End-to-End Happy Path + Smoke Script

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §6 (Day 15)
**Depends on:** [W2-F1](w2-f1-nginx-routing-tls.md) (Playwright navigates through port 80/443 as a browser; single entry point must be wired, else target :3000 directly), W3-F3 + W3-F4 (full quiz UI incl. timer + submit-lock must exist for the happy path), W3-F5 (smoke-script pattern reused as pre-flight health check)
**Unblocks:** — (top of the Week 3 slice; final vertical-slice verification)
**Last updated:** 2026-06-08

Drive a real browser through the full quiz-taking vertical slice against the
live Compose stack, and wire it into CI alongside a service smoke test.

## Steps

- [ ] **1. Install Playwright** — `npx playwright install --with-deps` in the
      frontend package; `playwright.config.ts` pointing at
      `http://localhost:3000`, Chromium as the default project.
- [ ] **2. Happy-path spec** — `tests/e2e/quiz-taking.spec.ts`: go to `/login`,
      fill a seeded candidate's credentials, assert redirect to dashboard,
      click Start on an assigned test, answer all questions via
      `page.locator`/`page.click`, Submit, assert the result page shows a score
      summary with all inputs disabled.
- [ ] **3. Smoke script** — shell script (extend `test-services.sh` or a new
      one) that `curl`s each service's `/health` in dependency order and exits
      non-zero on any non-200, so Playwright runs only against a
      confirmed-healthy stack.
- [ ] **4. CI job** — sequential job depending on the build matrix; `docker
      compose up -d --wait` for full-stack health, then smoke → Playwright.
- [ ] **5. Log artifact** — after each run, `docker compose logs --no-color >
      e2e-run.log` and upload as a CI artifact so failures trace across service
      boundaries without re-running locally.

## Notes

- Uses the seeded candidate (`password123`) — confirm an assigned test exists
  in the Alembic `0003` seed, or seed one in the smoke pre-flight.
- `test-services.sh` is stale/aspirational (references non-existent services);
  prefer a fresh smoke script over extending it. See
  [CLAUDE.md gotchas](../../CLAUDE.md).

## Remaining

All steps.
