# W3-F7 — Week-3 Review-Findings Remediation (trainer-defined)

**Status:** ❌ Not Started
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

- [ ] **1. (HIGH, W3-F4) Fix `useServerTimer` re-anchoring — countdown resets
      to full duration after every submit.**
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
- [ ] **2. (MED, W3-F4) Recovery path from a transient-exhausted submit.**
      After backoff exhaustion (~3.5s outage: 500+1000+2000ms),
      `SUBMIT_FAILED` locks the exam permanently — no reducer action exits
      `error` (`frontend/src/lib/exam/examReducer.ts:58-66`) and `TestRunner`
      renders no retry affordance. Spec only mandates halt for *semantic*
      errors; a brief network blip should not brick the attempt.
      **Fix:** add a `SUBMIT_RETRY` action (`error` → `active`, stays locked
      until the retried submit acks) + a "Retry submission" button in the
      error banner. Semantic errors (409/410/422) keep the terminal lock.
- [ ] **3. (MED, W3-F1 + W3-F3) Decide and implement active-session reuse.**
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
- [ ] **4. (MED, security, W3-F1) Role-gate `GET /questions/sample`.**
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
- [ ] **5. (MED, W3-F3) Error boundary for the take page.**
      `mintSessionServer` throws `ServerApiError` on 404 (bad testId), 422
      (empty question bank), 502 (question service down) and there is no
      `error.tsx` under `frontend/src/app/take/` — candidates get the raw
      Next.js 500 page. Add a route-level `error.tsx` ("couldn't start your
      test, try again / contact your trainer") and, for the 404 case, prefer
      `notFound()` + `not-found.tsx`.

### Hardening (do opportunistically, same branch or later)

- [ ] **6. (LOW, W3-F4) Autosave max-wait + halt-on-semantic.**
      `useAutosave` is a pure trailing debounce — a candidate answering more
      often than every 30s never persists a draft, and a failed save is only
      retried on the next change. Add a max-wait cap (fire at most every 30s
      while dirty, e.g. trailing debounce + leading throttle). Also stop
      autosaving after a semantic 409/410 (session is terminal — today the
      hook keeps PATCHing on every change; "surface and halt" is honored for
      submit but not autosave).
- [ ] **7. (LOW, W3-F3/F4, a11y) Associate question text with its option
      group + assert `aria-disabled`.**
      `CardTitle` question text is not programmatically tied to the inputs —
      add `aria-labelledby` on the `RadioGroup` / a fieldset-legend for the
      checkbox group. The W3-F4 spec names `aria-disabled` in step 5 but tests
      only assert `toBeDisabled()` — add the attribute assertion.
- [ ] **8. (LOW, W3-F1) `$sample` duplicate guard + short-fill visibility.**
      Mongo `$sample` may emit duplicate documents; dedupe `question_ids`
      before persisting (top up or accept the shorter set). When the bank
      holds fewer than `test.number_of_questions`, log a warning instead of
      silently short-filling.
- [ ] **9. (LOW, W3-F2) Idempotency + lock-scope notes.**
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

- Items 1–5 checked, with the new tests listed above green.
- W3-F4 timer behavior verified manually: answer ≥2 questions in a live
  session, countdown never increases.
- [FEATURE_STATUS.md](../FEATURE_STATUS.md): W3-F4 flips back to ✅ (its
  completion is gated on item 1), W3-F7 flips to ✅.
