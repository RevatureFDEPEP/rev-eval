# W3-F4 — Auto-Saving Exam Client (Server-Anchored Timer + Submit-Lock UX)

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §4 (Day 14)
**Depends on:** W3-F3 (extends the `TestRunner` component + answer `Map`), W3-F2 (`PATCH /sessions/{id}/draft` relies on the session state machine + status fields; submit-lock is only meaningful once server-side `submitted` is enforced)
**Unblocks:** W3-F6 (Playwright E2E — full quiz UI incl. timer + submit-lock must be present)
**Last updated:** 2026-06-12

Add a server-anchored countdown timer, autosave drafts, and an idempotent
submit-and-lock flow to the exam client.

## Steps

- [ ] **1. Server-anchored timer** — `useServerTimer(expiresAt)` hook derives
      remaining time from the server-issued `expires_at`; re-anchors on focus
      to prevent drift.
- [ ] **2. PATCH /sessions/{id}/draft** — endpoint in test-management-service
      that stores the current answer map without locking or scoring.
- [ ] **3. Error classification** — network errors, semantic errors (session
      already submitted), and retry affordance distinguished in UI.
- [ ] **4. Submit-and-lock via useReducer** — 6-state machine
      (`idle → submitting → submitted | error`); submit button disabled once
      `submitted`.
- [ ] **5. Component tests** — Vitest / Jest tests for the timer hook and the
      submit state machine.

## Evidence

None on `tianyac` branch per the spec. A brownfield quiz page at
`frontend/src/app/(dashboard)/participant/tests/take/mcq/[testId]/page.tsx`
contains timer and state-machine logic (commit `01d7a7f`, author JesterCharles)
but:
- not authored by tianyac
- not at the spec's path
- depends on W3-F2 `PATCH /draft` endpoint which does not exist on this branch

## Remaining

All steps. Blocked on [W3-F3](w3-f3-test-taking-frontend-skeleton.md) and
[W3-F2](w3-f2-scoring-engine-locking.md).
