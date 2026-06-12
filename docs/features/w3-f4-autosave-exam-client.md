# W3-F4 — Auto-Saving Exam Client (Server-Anchored Timer + Submit-Lock UX)

**Status:** ✅ Completed (re-opened 2026-06-10 by the post-merge review of
PR #76; closed the same day by W3-F7 — the step-1 timer defect, the retry
affordance, and the autosave/a11y hardening all landed on
`richardh-feat-W3F7`)
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
      server_now` parsed at mount; per-tick `remaining` re-derived from an
      absolute deadline so a throttled tab can't drift; `onExpire` fires once
      at zero). Wired in `TestRunner.tsx` with `onExpire={handleSubmit}`;
      display reuses `components/quiz/Timer.tsx`.
      **Re-open resolved (W3-F7 item 1, commit `1b26f49`):** the deadline is
      now anchored ONCE in a ref on the first enabled run — `enabled` toggles
      (every submit) re-derive from the same deadline instead of re-anchoring
      against the full baseline, and `onExpire` single-fires via a ref across
      re-enables. The missing disable→re-enable cycle test + multi-toggle and
      expiry-across-re-enable specs are in `useServerTimer.test.ts`.
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

None. The 2026-06-10 re-open items were all delivered by
[W3-F7](w3-f7-review-remediation.md) on `richardh-feat-W3F7`:

- **Step 1 defect (HIGH, W3-F7 item 1)** — fixed in `1b26f49`
  (deadline-once `useServerTimer` + disable→re-enable regression specs).
- **Recovery affordance (MED, W3-F7 item 2)** — `SUBMIT_RETRY` (transient-only
  exit from `error`) + "Retry submission" button, `5db0980`.
- **Hardening (LOW, W3-F7 items 6–7)** — autosave max-wait cap + semantic-409/410
  halt; `aria-labelledby`/fieldset question-group association and
  `aria-disabled` assertions, `7b2e6c4`.

At close of W3-F7: frontend `pnpm test` 130 pass / `pnpm lint` clean /
`pnpm build` green; backend `pytest` 100 pass + 6 integration vs real
containers; `alembic heads` → single head `0007`.

Decisions worth carrying forward (see the plan for rationale): forward motion is
the `POST /answer` loop (append `next_question`, finalize on the last question);
answered questions are reviewed read-only; draft autosave is advisory
last-write-wins (no scoring, no index/status change).
