# W3-F3 — Test-Taking Frontend Skeleton (Dynamic Routing + Auth Context)

**Status:** ✅ Done
**Spec:** `days_11_15_features.md` §3 (Day 13)
**Depends on:** W3-F1 (page calls `POST /sessions` server-side on load; endpoint must return the correct contract shape), [W2-F1](w2-f1-nginx-routing-tls.md) (frontend reaches the gateway through a single routed entry point, not cross-origin port calls), [W2-F6](w2-f6-question-authoring-ui.md) (question documents must exist in Mongo to sample and render)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `TestRunner` + answer `Map` are the base layer), W4-F2 (Results Page — reuses the AuthContext provider + cookie-forwarding pattern), W4-F4 (Trainer Dashboard — AuthContext supplies the role claim for client-side guards)
**Last updated:** 2026-06-18

Spec-compliant `/take/[testId]` page with server-component session creation,
`TestRunner` client component, polymorphic question rendering, and `AuthContext`.

## Steps

- [x] **1. Server-component page** — `frontend/src/app/take/[testId]/page.tsx`
      calls `POST /v1/api/sessions/` on the gateway server-side with the bearer
      token from the httpOnly cookie; passes `SessionRead` + `AuthUser` to
      `TestRunner`.
- [x] **2. TestRunner client component** — `frontend/src/app/take/[testId]/TestRunner.tsx`;
      owns `currentIndex`, `answers: Map<string, AnswerValue>`, and `questions`
      cache array (grows lazily as user advances).
- [x] **3. Polymorphic question render** — delegates to existing `QuestionCard`
      (`frontend/src/components/quiz/QuestionCard.tsx`) which dispatches to
      `MCQQuestion`, `MultiQuestion`, `TrueFalseQuestion` by `question_type`.
- [x] **4. Stateful Prev/Next** — Previous decrements `currentIndex` (no API
      call); Next navigates the cache or calls `submitAnswer()` via
      `frontend/src/lib/api/sessions.ts` to fetch the next question. No App
      Router navigation.
- [x] **5. AuthContext provider** — `frontend/src/context/AuthContext.tsx`
      exposes `{ id, email, role }` to the `TestRunner` subtree via
      `AuthProvider` + `useAuth()`. The server component reads identity from the
      JWT via `getSession()` (server-only); no token touches the client.

## Evidence

Commit `45eb3f4` on branch `test-taking-frontend`:
- `frontend/src/app/take/[testId]/page.tsx` — async server component
- `frontend/src/app/take/[testId]/TestRunner.tsx` — client component
- `frontend/src/context/AuthContext.tsx` — context + provider + hook
- `frontend/src/lib/api/sessions.ts` — `submitAnswer()` + `SessionRead`/`AnswerResponse` types
- `frontend/src/__tests__/app/take/TestRunner.test.tsx` — 9 tests
- `frontend/src/__tests__/context/AuthContext.test.tsx` — 3 tests

All 116 frontend tests pass (14 new, 102 existing). ESLint clean.

## Remaining

None.
