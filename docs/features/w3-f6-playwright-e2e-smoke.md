# W3-F6 — Playwright End-to-End Happy Path + Smoke Script

**Status:** ✅ Completed (branch `richardh-feat-W3F6`; plan: [docs/plans/w3-f6-playwright-e2e-smoke.md](../plans/w3-f6-playwright-e2e-smoke.md))
**Spec:** `days_11_15_features.md` §6 (Day 15)
**Depends on:** [W2-F1](w2-f1-nginx-routing-tls.md) (Playwright navigates through port 80/443 as a browser; single entry point must be wired, else target :3000 directly), W3-F3 + W3-F4 (full quiz UI incl. timer + submit-lock must exist for the happy path), W3-F5 (smoke-script pattern reused as pre-flight health check)
**Unblocks:** — (top of the Week 3 slice; final vertical-slice verification)
**Last updated:** 2026-06-11

Drive a real browser through the full quiz-taking vertical slice against the
live Compose stack, and wire it into CI alongside a service smoke test.

## Steps

- [x] **1. Install Playwright** — `@playwright/test` devDep +
      `frontend/playwright.config.ts`: `testDir tests/e2e`, Chromium-only
      project, `baseURL` env-overridable (`E2E_BASE_URL`, default
      `http://localhost:3000`), no `webServer` (stack runs externally).
      Browsers installed via `pnpm exec playwright install --with-deps
      chromium` (CI step does the same).
- [x] **2. Happy-path spec** — `frontend/tests/e2e/quiz-taking.spec.ts`:
      login as seeded `student4@revature.com` on `/` (the app has no `/login`
      route — the landing page is the auth form), assert redirect to
      `/participant/dashboard`, click **Start Test** (dashboard quiz links
      rewired to the W3-F3/F4 `/take/[testId]` TestRunner), answer every
      question via `getByRole('radio'/'checkbox')` + `submit-button` in a
      count-agnostic loop, submit, assert the locked `exam-confirmation`
      screen with **zero remaining inputs**. Green twice against the live
      stack (10.6s / 10.2s) — re-runnable since session reuse only grabs
      ACTIVE sessions. *Adaptation:* a score-summary assertion is
      intentionally absent — see Notes.
- [x] **3. Smoke script** — `scripts/smoke.sh` (fresh script;
      `test-services.sh` is stale): curls each `/health` in dependency order
      (user → question → test-management → reporting → gateway) then polls
      the frontend with a long first-compile budget; first failure exits
      non-zero naming the service (verified: stopping reporting → exit 1).
      `scripts/e2e-seed.sh` pre-flights the Mongo question bank (compose
      doesn't auto-seed it; an empty bank 422s session minting) — idempotent
      mongosh top-up to 30 mcq docs.
- [x] **4. CI job** — `e2e` job in `ci-pipeline.yml`, sequential after
      `backend-build-test` + `frontend-build-test` (tolerates path-filter
      skips), generates throwaway nginx certs (real ones are git-ignored),
      `docker compose up -d --build --wait`, seed → smoke → Playwright.
- [x] **5. Log artifact** — `if: always()`: `docker compose logs --no-color >
      e2e-run.log`, uploaded with `frontend/playwright-report/` as the
      `e2e-artifacts` artifact; stack torn down with `-v`.

## Notes

- Uses the seeded candidate (`password123`) — confirmed: Alembic `0003`
  assigns every test to every participant; `student4`/`student5` are
  all-ASSIGNED. The question bank is seeded by `scripts/e2e-seed.sh`.
- `test-services.sh` is stale/aspirational (references non-existent services);
  a fresh smoke script was written instead. See
  [CLAUDE.md gotchas](../../CLAUDE.md).
- **Score-summary gap (known, deliberate):** the spec asks the result page to
  show a score summary, but session finalize never writes `test_submissions`
  (the sessions/answers slice and the seeded submissions are parallel
  systems), and the answer endpoint is score-free by design (W3-F2). The
  just-taken test therefore shows no score anywhere yet; the E2E asserts the
  locked confirmation instead. Bridging finalize → submission (or reading
  scores from `answers`) belongs to the W4 reporting slice (W4-F1).
- **Defect found by the E2E (not fixed here):** legacy option-less
  `true_false` bank docs (pre-W2-F6 shape, `correct_answers: [true]`) render
  as "No options available" in the TestRunner — the legacy quiz page had a
  dedicated True/False widget, `/take` routes them to the options-based
  single-select. The spec tolerates these by submitting an empty answer
  (schema allows it). Worth a cleanup/migration note for the question bank.

## Remaining

Nothing.
