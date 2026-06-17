# W5-F5 — Timezone-aware submission timestamps

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: in-source
`TODO ... for POC`; catalogued in [technical-debt.md](../technical-debt.md) §8
(line 89).
**Depends on:** test-management-service (Alembic-owned schema).
**Unblocks:** correct cross-timezone ordering/reporting of submissions.
**Last updated:** 2026-06-17

## Problem

Submission timestamps are timezone-naive "for POC":

```
services/test-management-service/src/schemas/test_submission_schema.py:25,30
    # TODO: fix with timezone-aware DB ...
```

Naive datetimes invite off-by-TZ bugs once clients/servers span zones — and the
W4 reporting layer groups/orders by `submitted_at` (`/reports/timeseries`,
`/reports/aggregate`), so drift here skews trainer analytics, not just storage.

## Steps

- [ ] **1. Audit** every `datetime` write/read on the submission + session/answer
      path (model columns, schema defaults, scoring/finalize timestamps). Identify
      naive `datetime.utcnow()`-style sites.
- [ ] **2. Move to aware UTC** — store TZ-aware UTC (`DateTime(timezone=True)` +
      `datetime.now(timezone.utc)`); serialize ISO-8601 with offset. test-management
      schema is Alembic-owned → `alembic revision --autogenerate` for any column
      type change.
- [ ] **3. Reporting consistency** — confirm `/reports/timeseries` day-bucketing and
      `/reports/aggregate` still group correctly against aware timestamps (sqlite
      fixture + Postgres).
- [ ] **4. Tests** — schema round-trip preserves offset; a submission written in one
      offset orders correctly; reporting day-bucket unchanged for same-instant data.
- [ ] **5. Remove the POC TODO** once resolved.

## Out of scope

- Per-user timezone display preferences in the frontend — storage/correctness only.

## Acceptance

- [ ] Submission timestamps are TZ-aware UTC end-to-end; reporting unaffected/correct.
- [ ] Migration applies cleanly; tests green.
- [ ] `FEATURE_STATUS.md` row flipped to ✅; debt §8 TODO cross-referenced as closed.
