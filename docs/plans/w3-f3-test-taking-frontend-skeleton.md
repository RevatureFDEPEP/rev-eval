# W3-F3 — Test-Taking Frontend Skeleton (Dynamic Routing + Auth Context) — Plan

**Feature:** W3-F3 — Test-Taking Frontend Skeleton with Dynamic Routing and Auth Context
**Detail doc:** [`docs/features/w3-f3-test-taking-frontend-skeleton.md`](../features/w3-f3-test-taking-frontend-skeleton.md)
**Spec:** `days_11_15_features.md` §3 (Day 13), Implementation Details 1–5
**Depends on:** W3-F1 (`POST /sessions` contract — ✅), W2-F1 (Nginx routing — ✅), W2-F6 (questions in Mongo — ✅)
**Unblocks:** W3-F4 (autosave exam client — TestRunner + answers Map base), W4-F2 (results page — AuthContext + cookie-forward pattern), W4-F4 (trainer dashboard — AuthContext role claim)

## Locked decisions

- **Navigation model (user-approved):** *Build full machinery, seed 1.* TestRunner
  accepts a `questions[]` array and owns `currentIndex` + `answers` (`Map<string, number[]>`)
  + clamped Prev/Next + polymorphic render. The live W3-F1 session seeds the array
  with **only the first question** (the backend is strictly sequential —
  one question at a time, server-advanced on answer-submit). The multi-question
  navigation + answers-Map-preservation machinery is fully built and unit-tested
  against a 3-question fixture. **Answer submission / appending `next_question` is
  W3-F4 scope** — F3 does not call `POST /sessions/{id}/answer`. No backend changes;
  the W3-F1 contract is honored as-is.
- **New route, not the old runner.** Build `frontend/src/app/take/[testId]/page.tsx`
  (top-level, per the detail doc). The pre-existing
  `participant/tests/take/mcq/[testId]/page.tsx` is an older non-session client
  runner and is left untouched.
- **New leaf components** named per spec: `<SingleSelectQuestion>` (radio) and
  `<MultiSelectQuestion>` (checkbox), modeled on the existing
  `MCQQuestion`/`MultiQuestion` style but driven by the session/answers-Map shape.
- **AuthContext is server-seeded.** Identity (`id`/`email`/`role`) is fetched
  **server-side** in the page via `GET /v1/api/auth/me` and passed as initial props
  to a client `AuthProvider`; the httpOnly `auth_token` cookie never enters the JS
  bundle or `window`.

## Context — what exists now

- **Backend contract (W3-F1, done):** `POST /v1/api/sessions` →
  `SessionOut { session_id, session_token, server_now, expires_at, current_index,
  total_questions, question: SanitizedQuestion | null }`. `SanitizedQuestion =
  { id, type, question_text, options?, difficulty?, image_url? }` — answer key
  stripped. Only the **current** question is ever returned; `question_ids` live
  server-side. Gateway already routes `^/v1/api/sessions(/.*)?$` →
  test-management-service (`api-gateway-service/main.py:55`). **No ROUTES change needed.**
- **Auth plumbing (reuse):**
  - `frontend/src/lib/session.ts:45` `getSession()` → `{ userId, email, role, token, exp }`
    from the httpOnly `auth_token` cookie (decode-only).
  - `frontend/src/lib/api/server.ts` — `server-only`; `authedFetch(path)` (GET-only
    today) forwards `Bearer session.token` to `API_GATEWAY_URL`.
  - `GET /v1/api/auth/me` (user-service `auth_route.py:62`) → `UserResponse
    { id, email, full_name?, role, is_active, created_at }`; the gateway forwards
    `/v1/api/auth/*` and user-service validates the Bearer itself. Existing BFF
    `frontend/src/app/api/auth/me/route.ts` maps this to camelCase.
  - `frontend/src/lib/auth/useAuth.ts` — a client hook that fetches `/api/auth/me`;
    there is **no Context provider yet** (this feature adds one).
- **UI kit:** shadcn `radio-group.tsx`, `checkbox.tsx`, `label.tsx`, `card.tsx`,
  `button.tsx` under `frontend/src/components/ui/`.
- **Tests:** Vitest (`pnpm test` = `vitest run`) + `@testing-library/react` + jsdom
  are configured (`vitest.config.ts`, `vitest.setup.ts`); quiz components already
  have `*.test.tsx` siblings to model.

## Constraints / gotchas

- httpOnly cookie must **not** reach the client bundle — only derived identity
  (`id`/`email`/`role`) crosses to the client.
- Prev/Next use **React state only — no App Router navigation** (no `router.push`,
  no re-fetch), so the answers Map survives index switches (spec step 4).
- `answers` is `Map<string, number[]>` keyed by `question.id`; single-select stores
  a one-element array, multi-select a multi-element array of `option_id`s.
- Follow the W3-F1 contract verbatim; do not re-derive timing client-side and do not
  add a bulk-questions endpoint.

---

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W3F3`** off `richardh` before any code change; confirm with
  `git branch --show-current`.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — Server-side session mint + identity helpers
- `frontend/src/lib/api/types.ts` — add `SanitizedQuestion`, `SessionOut`, and
  `AuthIdentity { id, email, role }` types mirroring the backend contract.
- `frontend/src/lib/api/server.ts` — generalize `authedFetch(path, init?)` to accept
  method/body (default GET preserved for existing callers); add
  `mintSessionServer(testId: number): Promise<SessionOut>` (POST `/v1/api/sessions`)
  and `getIdentityServer(): Promise<AuthIdentity>` (GET `/v1/api/auth/me`).
- Commit: `feat(w3-f3): server-side session mint + identity fetch helpers`.

### M2 — AuthContext provider
- `frontend/src/lib/auth/AuthContext.tsx` — client `AuthProvider` taking
  `initialUser: AuthIdentity` (server-seeded) + `useAuthContext()` hook exposing
  `{ user_id, email, role }`. No cookie/token in the provider.
- Commit: `feat(w3-f3): server-seeded AuthContext provider`.

### M3 — Polymorphic leaf question components
- `frontend/src/components/take/SingleSelectQuestion.tsx` — radio group; props
  `{ question, selected: number[], onChange(ids: number[]) }`.
- `frontend/src/components/take/MultiSelectQuestion.tsx` — checkbox group; same
  prop shape (toggles into the array).
- Commit: `feat(w3-f3): single/multi-select question leaf components`.

### M4 — TestRunner client component
- `frontend/src/components/take/TestRunner.tsx` — `'use client'`; props
  `{ session: SessionOut }`. Owns `currentIndex` (number) + `answers`
  (`Map<string, number[]>`). Builds a local `questions[]` seeded from
  `session.question` (length 1 live). `renderQuestion(question)` dispatches on
  `question.type` → SingleSelect/MultiSelect. Prev/Next mutate `currentIndex` in
  state only, clamped to `[0, questions.length - 1]`; answers Map persists across
  switches. Shows identity via `useAuthContext()`.
- Commit: `feat(w3-f3): TestRunner with currentIndex + answers Map + Prev/Next`.

### M5 — `/take/[testId]` server-component page
- `frontend/src/app/take/[testId]/page.tsx` — async server component: read cookie
  via `getSession()` (redirect to `/` if absent), `mintSessionServer(testId)` +
  `getIdentityServer()` server-side, render
  `<AuthProvider initialUser={identity}><TestRunner session={session} /></AuthProvider>`
  so the first question is in the initial HTML (no client spinner).
- Commit: `feat(w3-f3): /take/[testId] server-component page minting session`.

### M6 — Unit tests (Vitest)
- `frontend/src/components/take/TestRunner.test.tsx` — with a **3-question fixture**:
  selecting an answer then Next→Prev preserves the answers Map; Prev/Next clamp at
  bounds; renderQuestion picks the right leaf by `type`; no router navigation occurs.
- `frontend/src/components/take/SingleSelectQuestion.test.tsx` /
  `MultiSelectQuestion.test.tsx` — render options, fire selection, assert `onChange`
  payload shape.
- `frontend/src/lib/auth/AuthContext.test.tsx` — provider exposes seeded identity.
- Commit: `test(w3-f3): TestRunner nav/answers-Map + leaf + AuthContext tests`.

### M7 — Requirements review + status docs
- Re-read the 5 detail-doc Steps + spec Implementation Details 1–5; verify each
  against the diff, citing `file:line`/commit.
- Update `docs/features/w3-f3-test-taking-frontend-skeleton.md` (check off steps,
  add evidence, clear "Remaining") and the `FEATURE_STATUS.md` W3-F3 row → ✅.
- Commit: `docs(w3-f3): mark feature complete + requirements review evidence`.

## Testing & validation

Run from `frontend/`:
- `pnpm test` (`vitest run`) — **all green**, including the new M6 specs.
- `pnpm lint` — clean (no new warnings/errors).
- `pnpm build` — succeeds (server/client component boundaries valid; no
  `server-only` import leaking client-side).
- Smoke (optional, if Docker available): `docker compose up --build`, log in as a
  seeded participant, hit `/take/<testId>` → first question renders in initial HTML
  (view-source shows question text), identity shows, `auth_token` absent from the JS
  bundle/`window`.

**Pass bar:** `pnpm test` + `pnpm lint` + `pnpm build` all succeed and every detail-doc
Step is evidenced in the requirements review.

## Push gate

Push `richardh-feat-W3F3` to origin **only if** tests + lint + build pass **and** the
requirements review confirms all 5 Steps. Otherwise stop, keep the branch local, and
report what's outstanding.
