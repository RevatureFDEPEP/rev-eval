# W3-F3 — Test-Taking Frontend Skeleton (Dynamic Routing + Auth Context)

**Status:** ✅ Completed
**Spec:** `days_11_15_features.md` §3 (Day 13)
**Depends on:** W3-F1 (page calls `POST /sessions` server-side on load; endpoint must return the correct contract shape), [W2-F1](w2-f1-nginx-routing-tls.md) (frontend reaches the gateway through a single routed entry point, not cross-origin port calls), [W2-F6](w2-f6-question-authoring-ui.md) (question documents must exist in Mongo to sample and render)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `TestRunner` + answer `Map` are the base layer), W4-F2 (Results Page — reuses the AuthContext provider + cookie-forwarding pattern), W4-F4 (Trainer Dashboard — AuthContext supplies the role claim for client-side guards)
**Last updated:** 2026-06-10

Build the `/take/[testId]` Next.js page that mints a session server-side,
renders questions polymorphically by type, and preserves answer state across
forward/back navigation — no loading flicker, no cookie in JS bundles.

## Steps

- [x] **1. Server-component page** — `frontend/src/app/take/[testId]/page.tsx`
      as an async server component. Read the `auth_token` cookie via
      `next/headers` and `POST /sessions` server-side so the first question is
      in the initial HTML (no client spinner).
      *(Spec writes `pep_session`; this repo's cookie is `auth_token` —
      follow the repo, see [CLAUDE.md auth flow](../../CLAUDE.md).)*
      → `frontend/src/app/take/[testId]/page.tsx` async server component awaits
      `getSession()` (reads `auth_token` via `next/headers` cookies,
      `src/lib/session.ts:9,46`) and `mintSessionServer(testId)` (`POST
      /v1/api/sessions`, `src/lib/api/server.ts`) before render — the first
      question ships in the initial HTML, no client spinner. Build registers
      `/take/[testId]` as a dynamic (ƒ) route. (commit `f40e527`)
- [x] **2. TestRunner client component** — receives the session object as a
      prop; owns all interactive state: `currentIndex` (number) and `answers`
      (`Map<string, number[]>`).
      → `frontend/src/components/take/TestRunner.tsx`: `'use client'`, prop
      `{ session: SessionOut }`, `useState(currentIndex)` +
      `useState<Map<string, number[]>>(answers)`. (commit `2b6c17c`)
- [x] **3. Polymorphic question render** — single `renderQuestion(question)`
      dispatch switching on `question.type` →`<SingleSelectQuestion>` (radio
      group) or `<MultiSelectQuestion>` (checkbox group) leaf components.
      → `renderQuestion()` in `TestRunner.tsx` switches on `question.type`
      (`multi` → `MultiSelectQuestion`, else → `SingleSelectQuestion`); leaves
      at `frontend/src/components/take/{SingleSelectQuestion,MultiSelectQuestion}.tsx`.
      (commits `165b862`, `2b6c17c`)
- [x] **4. Stateful Prev/Next** — increment/decrement `currentIndex` in React
      state only, **no App Router navigation**, so selections in the `answers`
      Map survive question switches and require no re-fetch.
      → `goPrev`/`goNext` call `setCurrentIndex` only (clamped to
      `[0, questions.length-1]`); no `next/navigation` import. Test
      `TestRunner.test.tsx` "preserves answers in the Map across Next/Prev"
      proves selections survive navigation. (commits `2b6c17c`, `345ae8e`)
- [x] **5. AuthContext provider** — reads display identity (`user_id`, `email`,
      `role`) from a server-fetched token-validation call and exposes it to the
      client tree **without** placing the raw cookie into `window` or JS
      bundles.
      → `getIdentityServer()` (`GET /v1/api/auth/me`, `src/lib/api/server.ts`)
      runs server-side; its `{ user_id, email, role }` seeds the client
      `AuthProvider` / `useAuthContext` (`src/lib/auth/AuthContext.tsx`) via the
      `initialUser` prop. Only the derived identity crosses the boundary — the
      httpOnly cookie/token never enters the bundle. (commits `2ce1f45`,
      `c2e1be4`)

## Notes

- Cookie name: the spec's `pep_session` is generic; rev-eval uses
  **`auth_token`** (httpOnly). Use the existing `getSession()` /
  `frontend/src/lib/api/server.ts` plumbing rather than inventing a new cookie.
- Server-side mint relies on the W3-F1 response contract — coordinate the shape
  so the page doesn't re-derive timing client-side.
- **Navigation model (locked decision):** the W3-F1 backend is strictly
  sequential — only the current question is exposed, advanced server-side on
  answer-submit (W3-F4 scope). So `TestRunner` builds the full
  `currentIndex` + `answers` Map + clamped Prev/Next machinery and seeds the
  live `questions` array with just `session.question`. The injectable
  `initialQuestions` prop is the seam W3-F4 uses to grow the array (and that the
  3-question navigation unit test exercises). F3 does **not** call
  `POST /sessions/{id}/answer`.

## Remaining

None — all five steps complete. Answer submission, the server-anchored timer,
autosave, and submit-lock are W3-F4.

Post-merge review follow-ups (2026-06-10), specced in
[W3-F7](w3-f7-review-remediation.md): route-level `error.tsx` for
`/take/[testId]` — session-mint failures (404/422/502) currently surface the
raw Next.js 500 page (item 5); refresh minting a fresh session is the
user-visible face of W3-F1's missing reuse guard (item 3); a11y —
`aria-labelledby` association between question text and its option group
(item 7).

## Validation evidence

- `pnpm test` — 92 passed (11 files), incl. 14 new W3-F3 specs
  (`TestRunner`, `SingleSelectQuestion`, `MultiSelectQuestion`, `AuthContext`).
- `pnpm lint` — 0 errors (17 pre-existing warnings in untouched `quiz/`,
  `trainer/` files; none in new `take/` or `auth/` code).
- `pnpm build` — succeeds; `/take/[testId]` registered as a dynamic (ƒ) route,
  server/client component boundaries valid (no `server-only` leak).
