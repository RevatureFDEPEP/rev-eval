# W3-F4 — Auto-Saving Exam Client (Server-Anchored Timer + Submit-Lock UX)

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §4 (Day 14)
**Depends on:** W3-F3 (extends the `TestRunner` component + answer `Map`), W3-F2 (`PATCH /sessions/{id}/draft` relies on the session state machine + status fields; submit-lock is only meaningful once server-side `submitted` is enforced)
**Unblocks:** W3-F6 (Playwright E2E — the full quiz UI incl. timer + submit-lock must exist for the happy path to complete)
**Last updated:** 2026-06-08

Layer a live countdown timer derived from **server** timing, periodic autosave,
graceful network-failure handling, and an immediate submit-and-lock interaction
on top of the Day 13 skeleton.

## Steps

- [ ] **1. Server-anchored timer** — on `TestRunner` mount compute remaining
      seconds as `(expires_at - server_now) - (Date.now()/1000 - mount_time)`
      to absorb client clock skew. `setInterval` decrement + render; at zero,
      call the submit handler automatically.
- [ ] **2. PATCH /sessions/{id}/draft** — backend endpoint in
      test-management-service that persists a partial answers payload **without**
      advancing `current_index` or changing status. Wire a **debounced**
      autosave from `TestRunner` on a 30s interval.
- [ ] **3. Error classification** — split fetch errors into **transient**
      (network timeout, 502/503/504 → exponential-backoff retry) vs.
      **semantic** (409/410/422 → surface and halt). No retry storms on a 422.
- [ ] **4. Submit-and-lock via useReducer** — on submit, immediately set
      `isLocked: true` before the server responds, disabling all inputs + the
      timer. Autosave and submission are both **confirmed** updates (wait for
      server ack; don't unlock until the server confirms, to avoid showing a
      rejected result).
- [ ] **5. Vitest component tests** — timer decrement logic, autosave debounce
      trigger, locked-state rendering (assert `disabled` / `aria-disabled` on
      interactive elements when `isLocked`). Evidence:
      `frontend/src/components/quiz/__tests__/`.

## Notes

- Vitest is the chosen frontend runner here — [W2-F2](w2-f2-unit-test-scaffolding.md)
  notes no runner is wired yet; this feature lands the first real frontend test
  suite, so it also closes part of W2-F2's frontend gap.
- Timer must derive from `server_now`/`expires_at` (W3-F1 contract), never the
  client clock alone.

## Remaining

All steps.
