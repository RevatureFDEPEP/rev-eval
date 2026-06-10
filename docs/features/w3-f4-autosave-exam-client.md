# W3-F4 — Auto-Saving Exam Client (Server-Anchored Timer + Submit-Lock UX)

**Status:** ✅ Completed
**Spec:** `days_11_15_features.md` §4 (Day 14)
**Depends on:** W3-F3 (extends the `TestRunner` component + answer `Map`), W3-F2 (`PATCH /sessions/{id}/draft` relies on the session state machine + status fields; submit-lock is only meaningful once server-side `submitted` is enforced)
**Unblocks:** W3-F6 (Playwright E2E — the full quiz UI incl. timer + submit-lock must exist for the happy path to complete)
**Last updated:** 2026-06-10
**Plan:** [`docs/plans/w3-f4-autosave-exam-client.md`](../plans/w3-f4-autosave-exam-client.md)

Layer a live countdown timer derived from **server** timing, periodic autosave,
graceful network-failure handling, and an immediate submit-and-lock interaction
on top of the Day 13 skeleton.

## Steps

- [x] **1. Server-anchored timer** — on `TestRunner` mount compute remaining
      seconds as `(expires_at - server_now) - (Date.now()/1000 - mount_time)`
      to absorb client clock skew. `setInterval` decrement + render; at zero,
      call the submit handler automatically.
      → `frontend/src/lib/exam/useServerTimer.ts` (baseline = `expires_at −
      server_now` parsed at mount; per-tick `remaining = baseline − (Date.now() −
      mountWall)` re-derived from wall-clock so a throttled tab can't drift;
      `onExpire` fires once at zero). Wired in `TestRunner.tsx` with
      `onExpire={handleSubmit}`; display reuses `components/quiz/Timer.tsx`.
- [x] **2. PATCH /sessions/{id}/draft** — backend endpoint in
      test-management-service that persists a partial answers payload **without**
      advancing `current_index` or changing status. Wire a **debounced**
      autosave from `TestRunner` on a 30s interval.
      → `services/test-management-service/src/v1/routes/session_route.py`
      (`save_draft`, `@router.patch("/{session_id}/draft")`),
      `src/services/session_service.py` `save_draft()` (returns unchanged
      `current_index`/`status`), `sessions.draft_answers` column +
      `alembic/versions/0006_add_session_draft_answers.py`. Frontend:
      `frontend/src/lib/exam/useAutosave.ts` (30s debounce) +
      `frontend/src/lib/api/sessions.ts` `saveDraft()`. The BFF proxy
      (`app/api/v1/[...path]/route.ts`) already forwards PATCH.
- [x] **3. Error classification** — split fetch errors into **transient**
      (network timeout, 502/503/504 → exponential-backoff retry) vs.
      **semantic** (409/410/422 → surface and halt). No retry storms on a 422.
      → `frontend/src/lib/exam/errors.ts` `classifyError()` + `fetchWithRetry()`
      (exp backoff on transient only; semantic throws immediately). `saveDraft`/
      `submitAnswer` are retry-wrapped; `TestRunner` surfaces the classified
      error in a `role="alert"` banner.
- [x] **4. Submit-and-lock via useReducer** — on submit, immediately set
      `isLocked: true` before the server responds, disabling all inputs + the
      timer. Autosave and submission are both **confirmed** updates (wait for
      server ack; don't unlock until the server confirms, to avoid showing a
      rejected result).
      → `frontend/src/lib/exam/examReducer.ts` (`SUBMIT_START` optimistically
      locks; `SUBMIT_CONFIRMED` is the confirmed update — finalized → `submitted`
      + stays locked, else → `active` + unlock; `SUBMIT_FAILED` → `error` + stays
      locked). Timer stops via `enabled = exam.status === 'active'` in
      `TestRunner.tsx`.
- [x] **5. Vitest component tests** — timer decrement logic, autosave debounce
      trigger, locked-state rendering (assert `disabled` / `aria-disabled` on
      interactive elements when `isLocked`).
      → `frontend/src/lib/exam/{useServerTimer,useAutosave,examReducer,errors}.test.ts`
      + `frontend/src/components/take/TestRunner.test.tsx` (30 tests; locked-state
      asserts `toBeDisabled()` on the radio + submit button while submitting and
      after a semantic error). Backend `save_draft` covered by 5 tests in
      `services/test-management-service/tests/test_session_service.py`.

## Notes

- Vitest is the chosen frontend runner here — [W2-F2](w2-f2-unit-test-scaffolding.md)
  notes no runner is wired yet; this feature lands the first real frontend test
  suite, so it also closes part of W2-F2's frontend gap.
- Timer must derive from `server_now`/`expires_at` (W3-F1 contract), never the
  client clock alone.

## Remaining

None — all 5 steps complete. Verification: frontend `pnpm test` 116 pass /
`pnpm lint` clean / `pnpm build` green; backend `pytest` 94 pass (incl. 5 new
`save_draft` tests); `alembic heads` → single head `0006`.

Decisions worth carrying forward (see the plan for rationale): forward motion is
the `POST /answer` loop (append `next_question`, finalize on the last question);
answered questions are reviewed read-only; draft autosave is advisory
last-write-wins (no scoring, no index/status change).
