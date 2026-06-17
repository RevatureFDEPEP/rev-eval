# W5-F2 — Fix `TestRepository.get_by_id` None-row crash

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: deferred from
[W3-F1](w3-f1-quiz-session-backend.md) Remaining; out-of-scope-noted in
[W3-F7](w3-f7-review-remediation.md) (line 177).
**Depends on:** none.
**Unblocks:** correct 404 behavior on any path that fetches a test by id.
**Last updated:** 2026-06-17

## Problem

`get_by_id` dereferences `test` in the `else` branch even when the row is missing:

```
services/test-management-service/src/repositories/test_repository.py:13-21
    test = result.scalars().first()
    if test and test.duration:
        test.duration_seconds = int(test.duration.total_seconds())
    else:
        test.duration_seconds = None   # test is None here when id not found → AttributeError
    return test
```

When `test_id` does not exist, `result.scalars().first()` returns `None`, the
`if test and ...` short-circuits to the `else`, and `None.duration_seconds = None`
raises `AttributeError` → unhandled 500 instead of a clean 404. `list_all`
(lines 22-30) iterates real rows so it is unaffected — this is `get_by_id`-only.

## Steps

- [ ] **1. Guard the None case** — return `None` early when no row is found, and
      only set `duration_seconds` on a real `Test`. Keep the `duration`/no-`duration`
      handling for found rows. Mirror the safe `list_all` pattern.
- [ ] **2. Caller check** — confirm the service/route layer maps a `None` return
      to a 404 (add the mapping if it currently assumes a non-None test).
- [ ] **3. Tests** — unit: `get_by_id` with a missing id returns `None` (no raise);
      with a row that has/lacks `duration` sets `duration_seconds` correctly. If a
      route exercises it, an integration check that an unknown test id → 404.

## Out of scope

- Broader repository refactor — single-method correctness fix only.

## Acceptance

- [ ] Fetching an unknown test id returns `None`/404, never raises.
- [ ] Existing `get_by_id` callers unchanged in behavior for valid ids.
- [ ] Tests green; `FEATURE_STATUS.md` row flipped to ✅ with evidence.
