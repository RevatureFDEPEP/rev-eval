# W5-F14 — Fingerprint idempotency bodies + shorten the answer lock window

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin:
[technical-debt.md](../technical-debt.md) §5; **repayment backlog item 6**. Both
sub-items were documented (not fixed) as W3-F7 item 9.
**Depends on:** W3-F2 (scoring/locking), W3-F5 (integration harness for proof).
**Unblocks:** correct idempotency semantics; less lock contention under concurrency.
**Last updated:** 2026-06-17

## Problem

- **Idempotency replay not body-fingerprinted** (med) — a retry with the *same*
  `Idempotency-Key` but a *different* body replays the original response, masking a
  client bug instead of 409/422-ing it.
  test-management-service `IdempotencyRepository` (W3-F7 item 9).
- **QMS fetch holds `SELECT FOR UPDATE`** (med) — `submit_answer` runs the outbound
  httpx question fetch (with retries/backoff) *while holding* the session row lock,
  so a slow QMS lengthens lock-hold time and serializes concurrent answerers more
  than necessary. test-management-service `session_service.submit_answer` (W3-F7 item 9).

## Steps

- [ ] **1. Body fingerprint** — hash the request body into the idempotency dedup row;
      same key + same body → replay (unchanged); same key + different body → 422
      (Stripe-style mismatch). Migration for the new column (Alembic).
- [ ] **2. Shorten the lock window** — move the QMS question fetch *before* taking
      `SELECT FOR UPDATE` and re-check inside the lock, so the outbound call no longer
      runs under the lock. Preserve the exactly-once 200/409 guarantee.
- [ ] **3. Tests (real DB)** — extend the W3-F5 integration suite: same-key/diff-body
      → 422; same-key/same-body → replay; concurrent double-answer still yields one
      200 + one 409 with `current_index` advanced once, now without the fetch under
      the lock. Unit-cover the fingerprint compare.

## Out of scope

- A distributed idempotency store — the existing repository pattern is sufficient.

## Acceptance

- [ ] Same-key/different-body is rejected (422), not silently replayed.
- [ ] The QMS fetch no longer runs under the row lock; exactly-once semantics intact.
- [ ] Integration + unit tests green; `FEATURE_STATUS.md` row ✅; debt §5 / repayment 6 cross-referenced.
