# Plan — W5-F2: Fix `TestRepository.get_by_id` None-row crash

**Feature:** W5-F2 — Fix `TestRepository.get_by_id` None-row crash
**Detail doc:** [docs/features/w5-f2-test-repository-none-crash.md](../features/w5-f2-test-repository-none-crash.md)
**Spec origin:** trainer-defined remediation (non-catalog); deferred from W3-F1, out-of-scope-noted in W3-F7 (line 177).
**Depends on:** none.
**Unblocks:** correct 404 behavior on any path that fetches a test by id.

## Context

`services/test-management-service/src/repositories/test_repository.py:14-21`:

```python
test = result.scalars().first()
if test and test.duration:
    test.duration_seconds = int(test.duration.total_seconds())
else:
    test.duration_seconds = None   # test is None here when id not found → AttributeError
return test
```

When `test_id` does not exist, `result.scalars().first()` returns `None`; the
`if test and ...` short-circuits to `else`, and `None.duration_seconds = None`
raises `AttributeError` → unhandled 500 instead of a clean 404.

**Verified during analysis:**
- **Step 2 (caller check) is already satisfied — no code change needed.** All
  three callers in `test_service.py` (`get_test_by_id:90`, `update_test:43`,
  `delete_test:83`) already do `if not test: raise ValueError("Test not found")`,
  and `test_route.py` maps that to a 404 (lines 44-45, 71-72, 97-98). They never
  get the chance today because the repo raises first. Fixing the repo to return
  `None` makes the existing 404 path work. This milestone is **verify-only**.
- `list_all` (22-31) and `list_by_creator` (66-80) iterate real rows, so they are
  unaffected — this is `get_by_id`-only, matching the detail doc.
- `session_repository.py` already dodges this bug with a direct select (its
  comment at line 16 documents the crash); leave it as-is — out of scope.
- Test infra: root `conftest.py` provides an in-memory SQLite `db_session`
  fixture; `tests/test_session_repository.py` is the reference pattern. `Test`
  model is constructed as `Test(name=..., number_of_questions=..., duration=timedelta(...))`.

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create `richardh-feat-W5F2` **off `richardh`** before any code change.
- **First commit = this plan file.**
- One commit per milestone (Conventional Commits).

## Milestones

### M1 — Plan (this file)
Commit `docs/plans/w5-f2-test-repository-none-crash.md`.
`docs(W5-F2): plan get_by_id None-row crash fix`

### M2 — Guard the None case
`services/test-management-service/src/repositories/test_repository.py` — rewrite
`get_by_id` to return early on a missing row and only set `duration_seconds` on a
real `Test`, mirroring the safe `list_all` pattern:

```python
@staticmethod
async def get_by_id(db: AsyncSession, test_id: int) -> Optional[Test]:
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalars().first()
    if test is None:
        return None
    test.duration_seconds = int(test.duration.total_seconds()) if test.duration else None
    return test
```

`fix(test-mgmt): guard None row in TestRepository.get_by_id (404 not 500)`

### M3 — Tests
Add `services/test-management-service/tests/test_test_repository.py` (matches the
`test_session_repository.py` shape, uses `db_session`):
- `get_by_id` with a missing id returns `None`, no raise.
- `get_by_id` on a row **with** `duration` sets `duration_seconds` to the integer
  seconds.
- `get_by_id` on a row **without** `duration` sets `duration_seconds` to `None`.

`test(test-mgmt): cover get_by_id missing/duration/no-duration paths`

### M4 — Requirements review + docs
Re-read detail doc Steps + Acceptance against the diff. Check off steps with
evidence; flip the `FEATURE_STATUS.md` W5-F2 row to ✅.
`docs(W5-F2): mark complete with evidence; flip FEATURE_STATUS row`

## Testing & validation

From `services/test-management-service/`:

```bash
pytest tests/test_test_repository.py -v
pytest --cov          # full suite stays green, coverage gate holds
```

**Pass bar:** new tests pass; full suite green; coverage gate not regressed.

## Requirements review (M4 detail)

| Acceptance criterion | Evidence |
|---|---|
| Unknown test id returns `None`/404, never raises | M2 `get_by_id` early return + existing `test_route.py:44-45` 404 map; M3 missing-id test |
| Existing callers unchanged for valid ids | `duration_seconds` still set on found rows; M3 with/without-duration tests |
| Tests green; FEATURE_STATUS flipped to ✅ | `pytest --cov` output; M4 doc edits |

## Push gate

Push `richardh-feat-W5F2` to origin **only if** all tests pass **and** every Step
+ Acceptance criterion is confirmed. Otherwise stop and report what's outstanding.
