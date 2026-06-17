# W3-F7 — Week-3 Review-Findings Remediation (trainer-defined)

**Status:** ❌ Not Started
**Spec:** trainer-defined, non-catalog (review findings from merged W3 PRs).
**Depends on:** W3-F1..F4 merged and reviewed
**Last updated:** 2026-06-12

Address code-review findings from the merged Week-3 PRs.

## Items

- [ ] **1. (HIGH, W3-F4) Fix `useServerTimer` re-anchoring** — timer must
      re-anchor to `expires_at` on tab focus, not reset from the client clock.
- [ ] **2. (MED, W3-F4) Recovery path from transient-exhausted submit** —
      retry affordance when submit fails due to transient network error.
- [ ] **3. (MED, W3-F1 + W3-F3) Active-session reuse** — decide and implement
      whether a second `POST /sessions` for the same test reuses the existing
      active session or creates a new one.
- [ ] **4. (MED, security, W3-F1) Role-gate `GET /questions/sample`** —
      endpoint must require TRAINER or ADMIN role.
- [ ] **5. (MED, W3-F3) Error boundary for the take page** — React error
      boundary around `TestRunner` with a user-facing fallback.
- [ ] **6. (LOW, W3-F4) Autosave max-wait + halt-on-semantic** — cap autosave
      interval; stop autosave loop after a semantic error (session submitted).
- [ ] **7. (LOW, a11y, W3-F3/F4) Aria labels** — associate question text with
      option group; assert `aria-disabled` on submit button after lock.
- [ ] **8. (LOW, W3-F1) `$sample` duplicate guard + short-fill visibility** —
      deduplicate sampled questions; surface when fewer questions than
      requested are available.
- [ ] **9. (LOW, W3-F2) Idempotency + lock-scope notes** — document idempotency
      guarantees and lock scope in the scoring engine.

## Evidence

None on `tianyac` branch. W3-F1..F4 not implemented on this branch, so
review findings have not been identified.

Note: another contributor addressed these items on branch
`richardh-feat-W3F7`; that work is not yet merged into `tianyac`.

## Remaining

All items. Blocked on W3-F1 through W3-F4.
