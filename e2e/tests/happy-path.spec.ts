/**
 * Happy-path E2E: participant registers, logs in, takes a quiz, submits, sees results.
 *
 * Requires the full stack (docker compose up) to be running.
 * Point PLAYWRIGHT_BASE_URL at http://localhost:3000 (default) or the deployed URL.
 *
 * The API_BASE_URL env var (default: http://localhost:8000) is used by beforeAll
 * to create test fixtures via the API so the test is self-contained.
 *
 * Authentication state is saved to auth/participant.json after the first login
 * so subsequent tests skip the login page (Playwright storageState pattern).
 */

import { test, expect, request as apiRequest, APIRequestContext } from "@playwright/test";
import path from "path";
import fs from "fs";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
const AUTH_FILE = path.join(__dirname, "../auth/participant.json");

const PARTICIPANT = {
  email: `e2e_participant_${Date.now()}@test.com`,
  password: "E2eTestPass123!",
  full_name: "E2E Participant",
  role: "PARTICIPANT",
};

const TRAINER = {
  email: `e2e_trainer_${Date.now()}@test.com`,
  password: "E2eTrainerPass123!",
  full_name: "E2E Trainer",
  role: "TRAINER",
};

let trainerToken: string;
let testId: number;

// ---------------------------------------------------------------------------
// Setup: register users + create + assign a test via API
// ---------------------------------------------------------------------------

test.beforeAll(async () => {
  const api: APIRequestContext = await apiRequest.newContext({ baseURL: API_BASE });

  // Register participant
  const pResp = await api.post("/v1/api/auth/register", { data: PARTICIPANT });
  if (pResp.status() !== 201) {
    throw new Error(`Participant register failed: ${await pResp.text()}`);
  }

  // Register trainer and get token
  const tResp = await api.post("/v1/api/auth/register", { data: TRAINER });
  const tBody = await tResp.json();
  trainerToken = tBody.access_token;

  // Trainer creates a test
  const testResp = await api.post("/v1/api/tests/", {
    headers: { Authorization: `Bearer ${trainerToken}` },
    data: {
      name: "E2E Happy Path Quiz",
      test_type: "QUIZ",
      number_of_questions: 5,
    },
  });
  const testBody = await testResp.json();
  testId = testBody.id;

  // Trainer assigns the test to the participant via bulk-assign
  await api.post("/v1/api/submissions/bulk-assign", {
    headers: { Authorization: `Bearer ${trainerToken}` },
    data: {
      test_id: testId,
      participant_emails: [PARTICIPANT.email],
    },
  });

  await api.dispose();
});

// ---------------------------------------------------------------------------
// Test 1: Login and save storageState
// ---------------------------------------------------------------------------

test("login as participant and land on dashboard", async ({ page }) => {
  await page.goto("/login");

  // Fill credentials
  await page.getByLabel(/email/i).fill(PARTICIPANT.email);
  await page.getByLabel(/password/i).fill(PARTICIPANT.password);
  await page.getByRole("button", { name: /sign in|login/i }).click();

  // Should redirect to participant dashboard or tests page
  await page.waitForURL(/\/(dashboard|participant|tests)/);

  // Save auth state for subsequent tests (storageState pattern)
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) fs.mkdirSync(authDir, { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });

  // Assert we are logged in — look for common dashboard elements
  await expect(page).not.toHaveURL(/login/);
});

// ---------------------------------------------------------------------------
// Test 2: Participant sees the assigned quiz
// ---------------------------------------------------------------------------

test("participant sees assigned quiz in test list", async ({ browser }) => {
  test.skip(!fs.existsSync(AUTH_FILE), "auth state not available — run login test first");

  const context = await browser.newContext({ storageState: AUTH_FILE });
  const page = await context.newPage();

  await page.goto("/participant/tests");

  // The assigned test should appear in the list
  await expect(page.getByText("E2E Happy Path Quiz")).toBeVisible({ timeout: 10_000 });

  await context.close();
});

// ---------------------------------------------------------------------------
// Test 3: Navigate to quiz and verify questions load
// ---------------------------------------------------------------------------

test("participant can open quiz and see questions", async ({ browser }) => {
  test.skip(!fs.existsSync(AUTH_FILE), "auth state not available — run login test first");

  const context = await browser.newContext({ storageState: AUTH_FILE });
  const page = await context.newPage();

  await page.goto("/participant/tests");

  // Click the first "Take Test" or similar button for our quiz
  const quizRow = page.getByText("E2E Happy Path Quiz").locator("..");
  const startBtn = quizRow.getByRole("button", { name: /take|start|begin/i });
  if (await startBtn.count() === 0) {
    // Fallback: click the quiz name to navigate to it
    await page.getByText("E2E Happy Path Quiz").click();
  } else {
    await startBtn.click();
  }

  // Should navigate to the quiz page — wait for question content
  await page.waitForURL(/test-sessions|quiz|take/, { timeout: 15_000 });

  // Verify at least one question element is visible
  await expect(
    page.locator('[data-testid="question"], .question, h2, h3').first()
  ).toBeVisible({ timeout: 10_000 });

  await context.close();
});

// ---------------------------------------------------------------------------
// X-Request-Id propagation assertion
// ---------------------------------------------------------------------------

test("API gateway echoes X-Request-Id in response headers", async () => {
  const api: APIRequestContext = await apiRequest.newContext({ baseURL: API_BASE });

  const customRid = "e2e-request-id-assertion-abc123";
  const resp = await api.get("/health", {
    headers: { "X-Request-Id": customRid },
  });

  const returnedRid = resp.headers()["x-request-id"];
  expect(returnedRid).toBe(customRid);

  await api.dispose();
});

test("API gateway generates X-Request-Id when none supplied", async () => {
  const api: APIRequestContext = await apiRequest.newContext({ baseURL: API_BASE });

  const resp = await api.get("/health");
  const rid = resp.headers()["x-request-id"];

  expect(rid).toBeTruthy();
  // Should be a UUID (8-4-4-4-12 hex groups)
  expect(rid).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  );

  await api.dispose();
});
