import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the quiz-taking happy-path.
 *
 * Runs against the locally running Compose stack (frontend on :3000). Start the
 * stack first: `docker compose up --build -d` from the repo root, then seed the
 * databases (see docs/features/quiz-taking-secure-slice.md). No `webServer` is
 * configured because the app is served by Compose, not by Playwright.
 */
export default defineConfig({
  testDir: './e2e',
  // The Compose frontend runs `next dev`, which compiles each route on first
  // hit — generous timeouts absorb that one-time cold-compile latency.
  timeout: 180_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    // Use the locally installed Chrome/Edge if the Playwright-bundled Chromium
    // could not be downloaded (set E2E_CHANNEL=chrome|msedge to force it).
    ...(process.env.E2E_CHANNEL ? { channel: process.env.E2E_CHANNEL } : {}),
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
