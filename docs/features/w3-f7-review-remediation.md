# W3-F7 — Week-3 Review-Findings Remediation (trainer-defined)

**Status:** ✅ Completed (2026-06-10, branch `richardh-feat-W3F7` — all nine
items delivered, 6–9 included; plan:
[`docs/plans/w3-f7-review-remediation.md`](../plans/w3-f7-review-remediation.md))
**Spec:** trainer-defined, non-catalog (same pattern as [W2-F8](w2-f8-pre-existing-defects.md)).
Source: code review of the merged Week-3 PRs — #72 (W3-F1), #74 (W3-F2),
#75 (W3-F3), #76 (W3-F4) — performed 2026-06-10.
**Depends on:** W3-F1..F4 merged (all are).
**Unblocks:** W3-F4 completion (item 1 is its acceptance blocker), W3-F6
(Playwright happy path should not script around a broken timer), W4-F3
(item 4 is its first concrete authorization target).
**Last updated:** 2026-06-10

The Week-3 vertical slice (sessions → scoring → take-page → exam client) merged
with one real defect and a set of cross-feature follow-ups that no single
feature owns. Track them here so they get fixed deliberately instead of
rediscovered one bug report at a time. Items are ordered by severity; 1–5 are
required, 6–9 are hardening.

## Items

### Required

- [x] **1. (HIGH, W3-F4) Fix `useServerTimer` re-anchoring — countdown resets
      to full duration after every submit.**
      → **Done, `1b26f49`.** Absolute deadline anchored once in a ref on the
      first enabled run (`useServerTimer.ts`); ticks re-derive from it, so
      `enabled` toggles never move the anchor; `onExpire` single-fires via a
      ref across re-enables. New specs: disable→re-enable continues from
      elapsed (90 → 85, not 120), deadline stable across 3 toggles, expiry
      across a re-enable fires exactly once.
      `frontend/src/lib/exam/useServerTimer.ts:50-71`: the effect captures
      `mountWall = Date.now()` on every run with deps `[enabled, baseline]`.
      `TestRunner` passes `enabled = exam.status === 'active'`, so each submit
      toggles active → submitting → active, re-running the effect with a fresh
      wall anchor against the **original full baseline** — `remaining` jumps
      back to the full session duration after question 1. Display is wrong for
      the rest of the exam and client-side auto-submit at zero effectively
      never fires near true expiry (the candidate hits a server 409/410
      instead; server expiry is currently the only real guard).
      **Fix:** anchor once — store an absolute client-clock deadline
      (`Date.now() + baseline*1000` in a `useRef` on first mount) and derive
      `remaining` from it on every tick, so re-enables don't move the anchor.
      **Test (the gap that let this slip):** a disable → re-enable cycle spec —
      advance fake timers, toggle `enabled` off/on, assert `timeRemaining`
      continues from elapsed time, not from the full baseline.
- [x] **2. (MED, W3-F4) Recovery path from a transient-exhausted submit.**
      → **Done, `5db0980`.** `SUBMIT_RETRY` exits `error` → `submitting`
      (still locked) only when the recorded failure is transient; semantic
      stays terminal and renders no button. `TestRunner` error banner gains
      "Retry submission" for transient failures. Reducer + component specs
      cover both kinds.
      After backoff exhaustion (~3.5s outage: 500+1000+2000ms),
      `SUBMIT_FAILED` locks the exam permanently — no reducer action exits
      `error` (`frontend/src/lib/exam/examReducer.ts:58-66`) and `TestRunner`
      renders no retry affordance. Spec only mandates halt for *semantic*
      errors; a brief network blip should not brick the attempt.
      **Fix:** add a `SUBMIT_RETRY` action (`error` → `active`, stays locked
      until the retried submit acks) + a "Retry submission" button in the
      error banner. Semantic errors (409/410/422) keep the terminal lock.
- [x] **3. (MED, W3-F1 + W3-F3) Decide and implement active-session reuse.**
      → **Done, `56923dd` — semantic (a) reuse.** `create_session` returns the
      existing live ACTIVE session (original `expires_at` with a fresh
      `server_now` anchor, `current_index`, question at that index, stored
      `draft_answers`); expired-ACTIVE flips to EXPIRED then mints fresh.
      Alembic `0007` dedupes existing ACTIVE duplicates and adds
      `uq_sessions_active_user_test (user_id, test_id) WHERE status='ACTIVE'`;
      the race loser catches `IntegrityError` and serves the winner's row.
      `TestRunner` seeds answers from `draft_answers` and offsets the counter.
      Integration: repeat POST → same `session_id` + clock; concurrent
      double-POST → both 201, same id, one ACTIVE row (verified on real
      Postgres and live through the gateway).
      `POST /sessions` mints unlimited ACTIVE sessions per (user, test)
      (`services/test-management-service/src/services/session_service.py` —
      no reuse check, no unique constraint), and the take-page makes it
      user-visible: every refresh of `/take/[testId]` re-samples questions,
      resets the clock, and orphans the prior row. Pick one semantic and
      enforce it server-side:
      (a) **reuse** — return the existing ACTIVE session (current
      `draft_answers` + `current_index` intact), or
      (b) **conflict** — 409 with the active `session_id` so the client can
      resume.
      Reuse (a) is the better candidate UX and makes refresh-recovery free.
      Either way add the partial-unique index (`user_id, test_id WHERE status
      = 'ACTIVE'`) as the race backstop — and unlike the cohort's other
      implementation (#73), catch the `IntegrityError` and serve the
      winner's row instead of a 500. Do this **before** W3-F6 freezes E2E
      behavior; extend the W3-F5 integration suite with the concurrent
      double-POST case.
- [x] **4. (MED, security, W3-F1) Role-gate `GET /questions/sample`.**
      → **Done, `16d7fe7`.** `require_answer_key_role` on `/sample` in
      question-management-service: present non-TRAINER/ADMIN `X-User-Role` →
      403; absent header (internal TMS sampler) → allowed. Other question
      reads documented + deferred to W4-F3 in the route docstring and Out of
      scope below. Tests: PARTICIPANT/unknown → 403, TRAINER/ADMIN/headerless
      → 200. Live smoke through the gateway: participant 403, trainer 200.
      Net-new in #72: the gateway pattern `^/v1/api/questions(/.*)?$` forwards
      `/questions/sample?size=100` for **any** authenticated role, and the QMS
      route returns full documents including `correct_answers`/`sample_answer`
      — a participant one curl away from the answer key of the whole bank.
      Same leak class as the pre-existing `/questions` + `/questions/{id}`
      reads, but bulk-convenient and added during a quiz feature.
      **Fix (minimum):** reject non-TRAINER/ADMIN `X-User-Role` on `/sample`
      in question-management-service (downstream services already trust the
      gateway's injected headers — this is one guard clause). Sweep the other
      question reads into the same guard or explicitly defer them to W4-F3
      with a note. Add a test: participant role → 403, trainer → 200.
- [x] **5. (MED, W3-F3) Error boundary for the take page.**
      → **Done, `37bd680`.** `page.tsx` maps a `ServerApiError` 404 to
      `notFound()` → new `not-found.tsx`; everything else (422 empty bank,
      502 service down) lands in the new route-level `error.tsx` with a
      `reset()` retry — safe now that minting is idempotent (item 3).
      `mintSessionServer` throws `ServerApiError` on 404 (bad testId), 422
      (empty question bank), 502 (question service down) and there is no
      `error.tsx` under `frontend/src/app/take/` — candidates get the raw
      Next.js 500 page. Add a route-level `error.tsx` ("couldn't start your
      test, try again / contact your trainer") and, for the 404 case, prefer
      `notFound()` + `not-found.tsx`.

### Hardening (do opportunistically, same branch or later)

- [x] **6. (LOW, W3-F4) Autosave max-wait + halt-on-semantic.**
      → **Done, `7b2e6c4`.** Debounce capped at `intervalMs` after the first
      unsaved change (continuous editing still persists every interval); a
      409/410 latches a halt flag — no further PATCHes on a terminal session.
      Specs: edits every 5s fire at the 30s cap; a 409 stops all later saves;
      non-semantic failures keep retry-on-next-change.
      `useAutosave` is a pure trailing debounce — a candidate answering more
      often than every 30s never persists a draft, and a failed save is only
      retried on the next change. Add a max-wait cap (fire at most every 30s
      while dirty, e.g. trailing debounce + leading throttle). Also stop
      autosaving after a semantic 409/410 (session is terminal — today the
      hook keeps PATCHing on every change; "surface and halt" is honored for
      submit but not autosave).
- [x] **7. (LOW, W3-F3/F4, a11y) Associate question text with its option
      group + assert `aria-disabled`.**
      → **Done, `7b2e6c4`.** `aria-labelledby` ties the `RadioGroup`
      (mcq/true_false) and a `fieldset` (multi) to the rendered `CardTitle`
      id. (`aria-labelledby` on the fieldset instead of an sr-only legend —
      same programmatic association without duplicating the question text in
      the DOM.) Tests assert the association on both group roles and
      `aria-disabled` on the locked radiogroup.
      `CardTitle` question text is not programmatically tied to the inputs —
      add `aria-labelledby` on the `RadioGroup` / a fieldset-legend for the
      checkbox group. The W3-F4 spec names `aria-disabled` in step 5 but tests
      only assert `toBeDisabled()` — add the attribute assertion.
- [x] **8. (LOW, W3-F1) `$sample` duplicate guard + short-fill visibility.**
      → **Done, `147692d`.** Order-preserving dedupe of `question_ids` before
      persisting (shorter set accepted); `logger.warning` when the final count
      is below `test.number_of_questions`. Unit tests cover dedupe, the
      warning, and its absence on a full sample.
      Mongo `$sample` may emit duplicate documents; dedupe `question_ids`
      before persisting (top up or accept the shorter set). When the bank
      holds fewer than `test.number_of_questions`, log a warning instead of
      silently short-filling.
- [x] **9. (LOW, W3-F2) Idempotency + lock-scope notes.**
      → **Done (documentation option), `147692d`.** (a) one-key-one-payload
      contract documented at the minting site in
      `frontend/src/lib/api/sessions.ts`; (b) lock-scope + timeout budget
      (10s × ≤3 attempts) documented at the `get_question` call inside
      `submit_answer`.
      (a) Replay does not fingerprint the request body — reusing a key with a
      different payload silently returns the old response; either hash the
      body into the dedup row (422 on mismatch, Stripe-style) or document the
      contract where keys are minted (`frontend/src/lib/api/sessions.ts`).
      (b) `question_client.get_question` (with retries/backoff) runs while
      holding the `SELECT FOR UPDATE` row lock — per-session blast radius
      only, but either move the fetch pre-lock with a re-check or document
      the timeout budget at the call site.

## Out of scope

- The pre-existing unauthenticated-read posture of `/questions` +
  `/questions/{id}` beyond the guard chosen in item 4 — full RBAC at the API
  layer is **W4-F3**.
- `TestRepository.get_by_id` None-crash — already tracked in
  [w3-f1-quiz-session-backend.md](w3-f1-quiz-session-backend.md) Remaining.
- Trivy base-image digest automation (Renovate/Dependabot) — noted in #77,
  CI-infra backlog, not a W3 feature gap.

## Acceptance

- [x] Items 1–5 checked, with the new tests listed above green — frontend
  130 pass / lint clean / build green; test-management-service 100 unit +
  6 integration (real Postgres + Mongo, Alembic head `0007`);
  question-management-service 35 pass; ruff clean on both services.
- [x] W3-F4 timer behavior — covered programmatically: the multi-toggle
  fake-timer specs prove `timeRemaining` is monotonically derived from one
  fixed deadline across repeated submit cycles (countdown can never
  increase). Live compose smoke exercised the backend slice (role gate
  403/200; double-POST reuse → one ACTIVE row). A human eyeball of the
  countdown across ≥2 submits in a browser is still recommended on review.
- [x] [FEATURE_STATUS.md](../FEATURE_STATUS.md): W3-F4 flipped back to ✅
  (item 1 closed), W3-F7 flipped to ✅.
