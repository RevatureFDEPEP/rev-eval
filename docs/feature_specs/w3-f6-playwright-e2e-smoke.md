# W3-F6 — Playwright End-to-End Happy-Path Test and Smoke Script

*Write a Playwright test that drives a real browser through the full quiz-taking vertical slice against the live Compose stack, and wire it into CI alongside a service smoke test.*

* **Curriculum Fit**: Day 15 (End-to-end UI testing with Playwright happy-path, end-to-end smoke testing patterns, distributed log analysis across services, vertical-slice integration).
* **Prerequisites**: Day 15 topics.
* **Cross-Week Dependencies**: Requires W2-F1 (Nginx Routing) — Playwright navigates through port 80/443 as a browser would; the single entry point must be wired or the test must target port 3000 directly with CORS issues bypassed. Requires W3-F3 and W3-F4 (Frontend Skeleton + Timer/Autosave) — the full quiz-taking UI must be in place for the happy-path flow to complete. Requires W3-F5 (Integration Tests) — the smoke script pattern established there is reused as the pre-flight health check before Playwright runs.
* **Time Estimate**: Without AI tools: 5–8 hours | With AI tools (Gemini/Claude Code): 2–4 hours

## Implementation Details

1. Install Playwright in the frontend package (`npx playwright install --with-deps`) and create `playwright.config.ts` pointing at `http://localhost:3000` with the Chromium project as the default.
2. Write one Playwright test in `tests/e2e/quiz-taking.spec.ts` covering the happy path: navigate to `/login`, fill credentials for a seeded candidate user, assert redirect to dashboard, click Start on an assigned test, answer all questions using `page.locator` and `page.click`, click Submit, and assert the result page shows a score summary with all inputs disabled.
3. Write a shell-script smoke test (`test-services.sh` extension or a separate script) that curls the `/health` endpoint of every service in dependency order and exits non-zero if any service returns a non-200 status, so the Playwright test only runs against a confirmed-healthy stack.
4. Wire the smoke test and Playwright test as a sequential CI job that depends on the build matrix completing successfully and uses `docker compose up -d --wait` to ensure the full stack is healthy before the browser tests execute.
5. After each Playwright test run, capture distributed logs from all containers using `docker compose logs --no-color > e2e-run.log` and upload the log file as a CI artifact so failures can be traced across service boundaries without re-running locally.
