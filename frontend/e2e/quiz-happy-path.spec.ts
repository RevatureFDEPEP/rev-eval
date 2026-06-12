import { test, expect, Page } from '@playwright/test';

/**
 * Happy-path: a participant logs in, takes a server-backed quiz under the live
 * countdown, answers every question, submits, and lands on a locked result.
 *
 * Exercises the real `/v1/api/sessions` slice end to end through the browser →
 * BFF → gateway → test-management-service → question-management-service.
 *
 * Preconditions (see docs/features/quiz-taking-secure-slice.md):
 *   - `docker compose up --build -d` is running.
 *   - Postgres seeded (seed_db.py) — user student1@revature.com / password123.
 *   - At least one active QUIZ test (id 1) and a non-empty question bank.
 */

const EMAIL = process.env.E2E_EMAIL || 'student1@revature.com';
const PASSWORD = process.env.E2E_PASSWORD || 'password123';
const QUIZ_TEST_ID = process.env.E2E_QUIZ_TEST_ID || '1';

async function login(page: Page) {
  await page.goto('/');
  await page.locator('#email').fill(EMAIL);
  await page.locator('#password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  // First visit to the participant area cold-compiles the route in dev mode.
  await page.waitForURL('**/participant/**', { timeout: 60_000 });
}

test('participant completes a quiz end-to-end and sees a locked result', async ({ page }) => {
  // Any browser confirm (e.g. unanswered-questions prompt) is accepted.
  page.on('dialog', (d) => d.accept());

  await login(page);

  // Go straight to the server-backed quiz take page (session minted on load).
  await page.goto(`/participant/tests/take/quiz/${QUIZ_TEST_ID}`);

  // First question + the server-driven countdown must render (the take route
  // is also cold-compiled on first hit in dev mode).
  await expect(page.getByText(/Question 1 of \d+/)).toBeVisible({ timeout: 60_000 });

  // Walk every question, picking an answer, until the Submit button appears.
  // Bounded loop so a UI regression can never hang the suite.
  for (let i = 0; i < 50; i++) {
    const radios = page.locator('input[type="radio"], input[type="checkbox"]');
    const trueButton = page.getByRole('button', { name: 'True', exact: true });

    if (await radios.count()) {
      await radios.first().check();
    } else if (await trueButton.count()) {
      await trueButton.first().click();
    }

    const next = page.getByRole('button', { name: 'Next', exact: true });
    if (await next.isVisible().catch(() => false)) {
      await next.click();
    } else {
      break;
    }
  }

  await page.getByRole('button', { name: 'Submit Quiz' }).click();

  // Locked result screen with an aggregate score.
  await expect(page.getByText('Quiz submitted')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Score:\s*\d/)).toBeVisible();
});
