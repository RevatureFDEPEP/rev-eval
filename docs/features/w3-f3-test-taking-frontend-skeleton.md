# W3-F3 — Test-Taking Frontend Skeleton (Dynamic Routing + Auth Context)

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §3 (Day 13)
**Depends on:** W3-F1 (page calls `POST /sessions` server-side on load; endpoint must return the correct contract shape), [W2-F1](w2-f1-nginx-routing-tls.md) (frontend reaches the gateway through a single routed entry point, not cross-origin port calls), [W2-F6](w2-f6-question-authoring-ui.md) (question documents must exist in Mongo to sample and render)
**Unblocks:** W3-F4 (Auto-Saving Exam Client — `TestRunner` + answer `Map` are the base layer), W4-F2 (Results Page — reuses the AuthContext provider + cookie-forwarding pattern), W4-F4 (Trainer Dashboard — AuthContext supplies the role claim for client-side guards)
**Last updated:** 2026-06-12

Spec-compliant `/take/[testId]` page with server-component session creation,
`TestRunner` client component, polymorphic question rendering, and `AuthContext`.

## Steps

- [ ] **1. Server-component page** — `app/take/[testId]/page.tsx` calls
      `POST /sessions` server-side and passes the session to the client
      component.
- [ ] **2. TestRunner client component** — answer `Map` state, session
      context.
- [ ] **3. Polymorphic question render** — `QuestionCard` dispatches by type
      (MCQ / MULTI / TRUE_FALSE / TEXT).
- [ ] **4. Stateful Prev/Next** — navigation without re-fetching; current
      index tracked in state.
- [ ] **5. AuthContext provider** — React context exposing `user` + `role`
      claim derived from the httpOnly cookie.

## Evidence

None on `tianyac` branch per the spec. A brownfield quiz page exists at
`frontend/src/app/(dashboard)/participant/tests/take/mcq/[testId]/page.tsx`
(commit `01d7a7f`, author JesterCharles, May 2026) but:
- different URL pattern than the spec's `/take/[testId]`
- no AuthContext provider
- not authored by tianyac
- depends on W3-F1 session backend which does not exist on this branch

## Remaining

All steps. Blocked on [W3-F1](w3-f1-quiz-session-backend.md).
