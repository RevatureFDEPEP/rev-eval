import { defineConfig, devices } from "@playwright/test";

/**
 * E2E configuration.
 * Set PLAYWRIGHT_BASE_URL to point at a running stack. The defaults (frontend on :3000,
 * gateway on :8000) need the dev override:
 *   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
 * Tests are skipped in normal CI — run only when the full stack is available.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
