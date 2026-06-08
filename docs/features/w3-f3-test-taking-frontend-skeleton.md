# W3-F3 — Test-Taking Frontend Skeleton (Dynamic Routing + Auth Context)

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §3 (Day 13)
**Depends on:** W3-F1 (page calls `POST /sessions` server-side on load; endpoint must return the correct contract shape), [W2-F1](w2-f1-nginx-routing-tls.md) (frontend reaches the gateway through a single routed entry point, not cross-origin port calls), [W2-F6](w2-f6-question-authoring-ui.md) (question documents must exist in Mongo to sample and render)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `TestRunner` + answer `Map` are the base layer), W4-F2 (Results Page — reuses the AuthContext provider + cookie-forwarding pattern), W4-F4 (Trainer Dashboard — AuthContext supplies the role claim for client-side guards)
**Last updated:** 2026-06-08

Build the `/take/[testId]` Next.js page that mints a session server-side,
renders questions polymorphically by type, and preserves answer state across
forward/back navigation — no loading flicker, no cookie in JS bundles.

## Steps

- [ ] **1. Server-component page** — `frontend/src/app/take/[testId]/page.tsx`
      as an async server component. Read the `auth_token` cookie via
      `next/headers` and `POST /sessions` server-side so the first question is
      in the initial HTML (no client spinner).
      *(Spec writes `pep_session`; this repo's cookie is `auth_token` —
      follow the repo, see [CLAUDE.md auth flow](../../CLAUDE.md).)*
- [ ] **2. TestRunner client component** — receives the session object as a
      prop; owns all interactive state: `currentIndex` (number) and `answers`
      (`Map<string, number[]>`).
- [ ] **3. Polymorphic question render** — single `renderQuestion(question)`
      dispatch switching on `question.type` →`<SingleSelectQuestion>` (radio
      group) or `<MultiSelectQuestion>` (checkbox group) leaf components.
- [ ] **4. Stateful Prev/Next** — increment/decrement `currentIndex` in React
      state only, **no App Router navigation**, so selections in the `answers`
      Map survive question switches and require no re-fetch.
- [ ] **5. AuthContext provider** — reads display identity (`user_id`, `email`,
      `role`) from a server-fetched token-validation call and exposes it to the
      client tree **without** placing the raw cookie into `window` or JS
      bundles.

## Notes

- Cookie name: the spec's `pep_session` is generic; rev-eval uses
  **`auth_token`** (httpOnly). Use the existing `getSession()` /
  `frontend/src/lib/api/server.ts` plumbing rather than inventing a new cookie.
- Server-side mint relies on the W3-F1 response contract — coordinate the shape
  so the page doesn't re-derive timing client-side.

## Remaining

All steps.
