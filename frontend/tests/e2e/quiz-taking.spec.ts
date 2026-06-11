/**
 * W3-F6 happy path: a seeded candidate logs in, starts an assigned quiz from
 * the dashboard, answers every question through the /take TestRunner, submits,
 * and lands on the locked confirmation screen.
 *
 * Pre-flight contract (CI runs these via the e2e job; locally run them once):
 *   docker compose up -d --build --wait
 *   ./scripts/e2e-seed.sh   # question bank (Mongo is not auto-seeded)
 *   ./scripts/smoke.sh      # every /health green + frontend compiled
 *
 * The spec is count-agnostic: it loops until the submit button flips from
 * "Submit Answer" to "Submit Exam" (15–30 questions per the Alembic 0003
 * tests; short-fill tolerated per W3-F7). It is re-runnable against a
 * persistent volume — session reuse only grabs ACTIVE sessions, so each run
 * mints a fresh one after the previous SUBMITTED.
 *
 * Deliberately absent: a score-summary assertion. Session finalize does not
 * write test_submissions (parallel systems until the W4 reporting slice), so
 * the just-taken test shows no score anywhere yet. Documented in
 * docs/features/w3-f6-playwright-e2e-smoke.md.
 */
import { test, expect, type Page } from '@playwright/test';

const CANDIDATE_EMAIL = 'student4@revature.com';
const CANDIDATE_PASSWORD = 'password123';

// Hard ceiling on the answer loop — largest seeded quiz is 30 questions.
const MAX_QUESTIONS = 40;

/** Pick the first option of the live question (radio for mcq/true_false,
 *  checkbox for multi) — correctness doesn't matter for the happy path. */
async function answerCurrentQuestion(page: Page): Promise<void> {
  const radios = page.getByRole('radio');
  if ((await radios.count()) > 0) {
    await radios.first().click();
    return;
  }
  await page.getByRole('checkbox').first().click();
}

test('candidate completes an assigned quiz end to end', async ({ page }) => {
  // 1. Login from the landing page.
  await page.goto('/');
  await page.locator('#email').fill(CANDIDATE_EMAIL);
  await page.locator('#password').fill(CANDIDATE_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();

  // 2. PARTICIPANT role lands on the participant dashboard.
  await page.waitForURL('**/participant/dashboard', { timeout: 30_000 });
  await expect(
    page.getByRole('heading', { name: /upcoming tests/i }),
  ).toBeVisible();

  // 3. Start the first assigned quiz → the W3-F3/F4 TestRunner.
  await page.getByRole('link', { name: 'Start Test' }).first().click();
  await page.waitForURL(/\/take\/\d+/, { timeout: 30_000 });

  // First question is server-rendered into the initial HTML, with the
  // countdown and the signed-in identity alongside it.
  const counter = page.getByText(/Question \d+ of \d+/);
  await expect(counter).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('auth-identity')).toContainText(CANDIDATE_EMAIL);

  const submitButton = page.getByTestId('submit-button');

  // 4. Answer-to-advance loop: the backend is strictly sequential, so each
  // submit either appends the next question or finalizes the session.
  for (let i = 0; i < MAX_QUESTIONS; i += 1) {
    await expect(submitButton).toBeEnabled();
    const isLast = (await submitButton.textContent())?.trim() === 'Submit Exam';

    await answerCurrentQuestion(page);

    if (isLast) {
      await submitButton.click();
      break;
    }

    const before = (await counter.textContent()) ?? '';
    await submitButton.click();
    // Advance is confirmed by the counter moving on (e.g. 3 of 20 → 4 of 20).
    await expect(counter).not.toHaveText(before, { timeout: 30_000 });
  }

  // 5. Locked confirmation replaces the exam UI: no answer inputs remain.
  const confirmation = page.getByTestId('exam-confirmation');
  await expect(confirmation).toBeVisible({ timeout: 30_000 });
  await expect(confirmation).toContainText(/exam submitted/i);
  await expect(page.getByRole('radio')).toHaveCount(0);
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  await expect(page.getByTestId('submit-button')).toHaveCount(0);

  // 6. The participant tests list stays reachable after submission.
  await page.goto('/participant/tests');
  await expect(page.getByRole('table')).toBeVisible({ timeout: 30_000 });
});
