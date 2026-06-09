# W2-F2 Revision — Close Remaining Gaps

## Context

`docs/features/w2-f2-unit-test-scaffolding.md` was downgraded ✅ Completed → 🟡 In
Progress after a re-audit against the spec (`days_6_10_features.md` §2, Days 5 &
7). Two deliverables the spec names explicitly are still missing from the
reference implementation:

1. **Frontend** — spec §2.1 requires tests for **login layouts** and **Zod
   client utility schemas**. Today only 4 quiz presentation-component tests +
   the question-form-utils test exist. The login UI (`LandingAuth`) has no test,
   and there is no dedicated Zod-schema validation suite.
2. **Docker test stage** — spec §2.3 requires the multi-stage `test` stage to
   run pytest **inside the container during CI**. The stage exists in all four
   backend Dockerfiles (`base → test → production`) but CI builds the default
   `production` target, so the `test` stage is built-never-run and gates nothing.

Goal: implement both, flip the doc back to ✅ Completed, on a fresh feature
branch off `richardh`.

## Branch

```
git switch richardh && git switch -c richardh-feat-w2f2
```

## Changes

### 1. Login-layout test (frontend)

New: `frontend/src/app/_components/landing-auth.test.tsx`
Target: `LandingAuth` (`frontend/src/app/_components/landing-auth.tsx`).
Mock `next/navigation` `useRouter` (push/refresh) and global `fetch`. Use
`@testing-library/react` + `@testing-library/user-event` (already devDeps; vitest
+ jsdom env already configured via `vitest.config.ts` / `vitest.setup.ts`).

Cases:
- Renders login tab by default (Sign in / Email / Password; no full-name/role).
- Switching to Register tab reveals Full name + Role select + 8-char hint.
- Login submit → `fetch('/api/auth/login', {POST, body:{email,password}})`; on
  `res.ok` → `router.push('/dashboard')` + `router.refresh()`.
- Register submit → `fetch('/api/auth/register', body:{email,password,full_name,role})`.
- `!res.ok` → renders `data.detail` (or fallback) error text, no navigation.
- `fetch` throws → renders the network-error message.
- Submitting disables the button ("Working…").

### 2. Dedicated Zod-schema suite (frontend)

New: `frontend/src/components/trainer/__tests__/question-schemas.test.ts`
Target the exported schemas/factory in `question-form-utils.ts`:
- `imageFileSchema` — rejects non-png/jpg `File`, rejects > `MAX_IMAGE_BYTES`
  (5 MB), accepts a valid png/jpg under the limit.
- `buildQuestionSchema(mode, type)` per branch:
  - `baseSchema` rules: `question_text` ≥ 10 chars; `skills` 1–20; `tags`
    comma-string → trimmed array transform; `difficulty` enum.
  - create mcq (`createOptionsSchema`): 2–5 options, ≥1 correct.
  - edit mcq (`editMcqSchema`): exactly 1 correct.
  - edit multi (`editMultiSchema`): ≥1 correct but not all.
  - `trueFalseSchema`: requires boolean `true_false_answer`.
  - `textSchema`: `sample_answer` ≥ 10 chars.

Standalone suite per the chosen "full dedicated" scope — exhaustive per branch,
even where it overlaps the existing `question-form-utils.test.ts`.

Verify with `cd frontend && pnpm test` (vitest run) — all suites green; then
`pnpm lint` stays clean. No coverage gate on the frontend, so no threshold edits.

### 3. Wire `--target test` into CI (backend)

Edit `.github/workflows/ci-pipeline.yml`, backend matrix job
(`backend-build-test`). Add a step before the existing "Build Docker image"
(production) step:

```yaml
      - name: Build & run container test stage
        working-directory: services/${{ matrix.service }}
        run: docker build --target test -t ${{ matrix.service }}-test:${{ github.sha }} .
```

This executes the Dockerfile `test` stage (`pytest -q` inside the container) so
the build fails if container-level tests fail — satisfying spec §2.3. The
existing runner-level `pytest --cov` step stays (it produces `coverage.xml` for
the artifact + the `.coveragerc` `fail_under` ratchet); the production build +
Trivy scan steps are unchanged. `docker-compose.yml` is left alone (production
target on `up` is correct — tests must not run on normal startup).

### 4. Doc update

`docs/features/w2-f2-unit-test-scaffolding.md`:
- Status 🟡 In Progress → ✅ Completed; bump **Last updated** to 2026-06-09.
- Step 1 sub-bullet `[~] → [x]`: note the new `landing-auth.test.tsx` +
  `question-schemas.test.ts`; drop the "spec-named ... missing" caveat.
- Step 3 `[~] → [x]`: note CI now builds `--target test` per service; remove the
  "built but never run" gap text.
- Delete the **Remaining** section (both items now done).

## Verification

1. `cd frontend && pnpm test` → existing 35 + new login + schema tests pass.
2. `cd frontend && pnpm lint && pnpm build` → green.
3. Container test stage locally (sanity, one service):
   `docker build --target test services/test-management-service` → pytest runs,
   build succeeds. (CI runs this for all four.)
4. Backend runner tests unaffected: `cd services/test-management-service &&
   pytest -q` still green.
5. Commit per logical unit (frontend tests / CI wire-up / doc) and push
   `richardh-feat-w2f2` to origin once tests pass.

## Out of scope

- No new backend tests / coverage-threshold changes (backend half already met
  spec; only the container-run wiring was missing).
- No `docker-compose.yml` change.
- `testFormSchema` in the create/edit pages is inline (not exported) — not
  unit-tested here; the exported `question-form-utils` schemas are the
  spec's "client utility schemas."
