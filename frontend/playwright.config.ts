/**
 * Playwright config for the W3-F6 happy-path E2E suite.
 *
 * The suite runs against an externally started stack (`docker compose up -d
 * --wait` + scripts/e2e-seed.sh + scripts/smoke.sh) — there is deliberately no
 * `webServer` block; the browser talks to the compose frontend on :3000 by
 * default. Override the entry point with E2E_BASE_URL (e.g. https://localhost
 * to go through nginx — pair it with ignoreHTTPSErrors for the self-signed
 * cert).
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // The happy path mutates shared seeded state (one session per user/test) —
  // a single worker keeps runs deterministic.
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
