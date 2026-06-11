# W3-F6 — Playwright E2E Happy Path + Smoke Script

**Feature:** [w3-f6-playwright-e2e-smoke.md](../features/w3-f6-playwright-e2e-smoke.md)
**Spec:** `days_11_15_features.md` §6 (Day 15)
**Depends on:** W2-F1 (nginx ✅), W3-F3 + W3-F4 (`/take/[testId]` TestRunner ✅), W3-F5 (smoke/compose-in-CI pattern ✅)
**Unblocks:** — (top of the Week 3 slice)
**Branch:** `richardh-feat-W3F6` off `richardh`

**Locked decisions (user-approved):**

1. **Entry path** — rewire the participant dashboard quiz "Start Test" link from
   the legacy `/participant/tests/take/mcq/[testId]` page to `/take/[testId]`
   (the W3-F3/F4 TestRunner). The E2E clicks Start as the spec demands and
   exercises the timer/autosave/submit-lock UI the feature depends on.
2. **Score summary** — the spec's "result page shows a score summary" cannot be
   met as written: session finalize never writes `test_submissions` (sessions/
   answers and the seeded submissions are parallel systems), so the just-taken
   test stays ASSIGNED with score "—" on the tests list. The E2E asserts the
   submitted-confirmation lock state instead; the gap is documented as a defect
   note for the W4 reporting slice. No backend bridge in this feature.
3. **Target** — Playwright `baseURL` defaults to `http://localhost:3000` (spec
   step 1 literal), overridable via `E2E_BASE_URL`. CI still generates
   throwaway nginx certs so full-stack `docker compose up -d --wait` passes.

## Context

What exists now:

- `/take/[testId]` (`frontend/src/app/take/[testId]/page.tsx`) mints a session
  server-side and renders `TestRunner` (`frontend/src/components/take/TestRunner.tsx`):
  sequential submit-to-advance, `data-testid="submit-button"` ("Submit Answer" →
  "Submit Exam" on the last question), post-finalize confirmation card
  `data-testid="exam-confirmation"` that replaces all inputs. Options render as
  Radix radio groups (`role="radio"`) / checkboxes (`role="checkbox"`).
- Login is the landing page `/` (`landing-auth.tsx`): `#email`, `#password`,
  button "Sign in"; PARTICIPANT redirects to `/participant/dashboard`.
- Participant dashboard (`(dashboard)/participant/dashboard/page.tsx:174-204`)
  lists assigned tests with a "Start Test" button — currently linking the
  legacy mcq page (decision 1 rewires the quiz href).
- Seeds: user-service startup seeds `student1–5@revature.com` / `password123`;
  TMS Alembic `0003` assigns every test to every participant — student4/5 are
  all-ASSIGNED (clean candidates). Quiz tests sample 15–30 questions
  (`number_of_questions`); short-fill is tolerated (W3-F7) but an **empty**
  Mongo bank 422s session mint — the question bank is NOT auto-seeded by
  compose (`seed_rag_context_questions.py` needs `httpx`, absent in the QMS
  image), so E2E needs a pre-flight seed.
- W3-F7 session-reuse: `POST /sessions` reuses only ACTIVE sessions; a
  SUBMITTED one is left behind and a fresh session mints — the E2E is
  re-runnable against a persistent dev volume.
- All 5 backend services expose `/health` and have compose healthchecks; the
  frontend compose service (dev target) has none — the smoke script polls it.
- nginx TLS certs are generated locally and git-ignored (`nginx/certs/`); CI
  must create throwaway certs or full-stack `--wait` hangs on nginx.
- `test-services.sh` is stale (Consul/Lambda/WorkOS) — write a fresh script,
  per the detail-doc note.
- CI (`.github/workflows/ci-pipeline.yml`): `backend-build-test` matrix +
  `frontend-build-test`; the W3-F5 integration step (lines ~130–147) is the
  compose-in-CI pattern to reuse. Frontend job pins pnpm via
  `pnpm/action-setup@v4` + Node 20.
- Vitest `include` is `src/**/*.test.{ts,tsx}` — `tests/e2e/` won't collide
  with `pnpm test`.

## Implementation steps

### 0. Branch & commit workflow

- `git fetch && git pull origin richardh`.
- Create **`richardh-feat-W3F6`** off `richardh` before any code change.
- **First commit = this plan file.**
- One Conventional-Commits commit per milestone below.

### M1 — Playwright install + config (spec step 1)

Files: `frontend/package.json`, `frontend/playwright.config.ts`,
`frontend/.gitignore` (or root), `frontend/tests/e2e/` (created in M3).

- Add `@playwright/test` to `devDependencies`; script
  `"test:e2e": "playwright test"`.
- `playwright.config.ts`: `testDir: './tests/e2e'`, `baseURL:
  process.env.E2E_BASE_URL ?? 'http://localhost:3000'`, single **Chromium**
  project, `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`,
  CI retries 1, no `webServer` (the stack runs externally via compose).
- Ignore `playwright-report/`, `test-results/`.
- Local browser install: `pnpm exec playwright install --with-deps chromium`.

Commit: `feat(W3-F6): add Playwright config and e2e scaffolding`

### M2 — Dashboard Start → /take rewire (decision 1)

Files: `frontend/src/app/(dashboard)/participant/dashboard/page.tsx` (+ its
test file if hrefs are asserted).

- Quiz href becomes `/take/${test.test_id}` for ASSIGNED (Start Test) and
  IN_PROGRESS (Continue Test — W3-F7 reuse semantics make resume work).
  Interview hrefs untouched. Legacy mcq page itself is left in place.
- Run frontend unit suite; update any href-asserting tests.

Commit: `feat(W3-F6): point dashboard quiz links at /take TestRunner`

### M3 — Happy-path spec (spec step 2, adapted per decision 2)

Files: `frontend/tests/e2e/quiz-taking.spec.ts`.

Flow (seeded candidate `student4@revature.com` / `password123`):

1. `goto('/')` → fill `#email` / `#password` → click "Sign in".
2. Assert redirect to `/participant/dashboard`.
3. Click the first "Start Test" button → assert URL `/take/<id>` and the
   first question + timer render.
4. Answer loop (count-agnostic, handles 15–30 questions and short-fill):
   while the submit button reads "Submit Answer" — check the first
   `role=radio`/`role=checkbox` option, click `submit-button`, wait for the
   question index to advance.
5. On "Submit Exam": click, assert `exam-confirmation` is visible and **no
   enabled inputs remain** (`radio`/`checkbox` count = 0).
6. Navigate to `/participant/tests`; assert the tests table renders (reachable
   post-submit). Score-summary assertion is **intentionally absent** —
   documented gap (decision 2).

Selectors stick to roles, labels, and the existing `data-testid`s
(`submit-button`, `exam-confirmation`, `auth-identity`).

Commit: `test(W3-F6): Playwright happy-path quiz-taking spec`

### M4 — Smoke + seed scripts (spec step 3)

Files: `scripts/smoke.sh`, `scripts/e2e-seed.sh` (new; `test-services.sh`
left untouched as documented-stale).

- `smoke.sh`: curl each HTTP `/health` in dependency order — user-service
  :8002 → question-management-service :8003 → test-management-service :8001 →
  reporting :8004 → gateway :8000 — then poll frontend :3000 `/` for HTTP 200
  (long timeout: dev-server first-compile). Per-service retry loop
  (`--max-time` + N attempts); first hard failure exits non-zero with the
  failing service named.
- `e2e-seed.sh`: idempotent question-bank seed via
  `docker compose exec -T mongo mongosh` — if the questions collection holds
  fewer than ~30 docs, insert 30 `mcq` documents (shape mirrored from the
  W3-F5 integration fixture: `options[{option_id,text}]`, `correct_answers`,
  tagged `e2e-seed`). No host-side Python/pip needed.

Commit: `feat(W3-F6): smoke health-check and e2e question-seed scripts`

### M5 — CI job + log artifact (spec steps 4–5)

Files: `.github/workflows/ci-pipeline.yml`.

New `e2e` job, `needs: [backend-build-test, frontend-build-test]`:

1. checkout; `cp .env.example .env`.
2. Generate throwaway nginx certs:
   `openssl req -x509 -newkey rsa:2048 -nodes -keyout nginx/certs/localhost.key
   -out nginx/certs/localhost.crt -days 1 -subj "/CN=localhost"`.
3. `docker compose up -d --build --wait` (full stack).
4. `./scripts/e2e-seed.sh` then `./scripts/smoke.sh`.
5. pnpm/Node setup (mirror frontend job), `pnpm install`,
   `pnpm exec playwright install --with-deps chromium`, `pnpm test:e2e`.
6. `if: always()` — `docker compose logs --no-color > e2e-run.log`;
   `actions/upload-artifact` for `e2e-run.log` + `frontend/playwright-report/`.
7. `if: always()` — `docker compose down -v --remove-orphans`.

Commit: `ci(W3-F6): sequential e2e job with smoke gate and log artifact`

### M6 — Requirements review + docs

- Re-read detail-doc Steps + spec §6; verify each against the diff with
  file:line evidence.
- Update `docs/features/w3-f6-playwright-e2e-smoke.md` (check steps, evidence,
  Notes: score-summary gap + sessions→submissions defect pointer for W4) and
  the `FEATURE_STATUS.md` row (❌ → ✅, headline note).

Commit: `docs(W3-F6): check off feature steps and update status tracker`

## Testing & validation

- **Frontend units:** `pnpm test` (130 green today) + `pnpm lint` +
  `pnpm build` — must stay green after M1/M2.
- **E2E local:** `docker compose up -d --build --wait` →
  `./scripts/e2e-seed.sh` → `./scripts/smoke.sh` (exit 0) →
  `pnpm test:e2e` — happy path passes against the live stack. Re-run once to
  prove re-runnability (session-reuse leaves SUBMITTED behind).
- **Smoke negative check:** stop one service, run `smoke.sh`, confirm
  non-zero exit naming the service.
- **Backend suites untouched** — no service code changes expected; spot-run
  TMS units if anything backend-adjacent moves.
- Pass bar: all of the above green locally; CI `e2e` job verified on the
  pushed branch (post-push, first run may need iteration — report status).

## Push gate

Push `richardh-feat-W3F6` **only if** frontend units/lint/build pass, the
local E2E run passes, and the M6 review confirms every Step (with the
documented score-summary adaptation). Otherwise stop and report what's
outstanding.
