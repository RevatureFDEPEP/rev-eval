# W5-F6 — user-service repository layer + unit tests

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: empty stub +
thin coverage; catalogued in [technical-debt.md](../technical-debt.md) §5
(line 69); noted in [W2-F2 plan](../plans/w2-f2-unit-test-scaffolding.md) lines 49,85.
**Depends on:** user-service.
**Unblocks:** testable data-access seam for user-service; CI coverage where there
is currently none.
**Last updated:** 2026-06-17

## Problem

`services/user-service/src/repositories/user_repository.py` is an **empty stub** —
data access is inlined elsewhere and tests target the model directly
(`services/user-service/conftest.py:32`) because there is no repository to test.
CI skips coverage for services with no `tests/` dir (debt §5), so user-service
regressions land silently.

## Steps

- [ ] **1. Implement the repository** — extract user data access (get by
      id/email, create, list, update) into `UserRepository`, matching the layered
      pattern used by the other FastAPI services (async SQLAlchemy). Route the
      service layer through it instead of inlining queries.
- [ ] **2. Add `services/user-service/tests/`** with a hermetic test DB fixture
      (mirror test-management-service's aiosqlite/itest pattern), so CI's
      `pytest --cov` activates for this service.
- [ ] **3. Repository unit tests** — get-by-email hit/miss, create + uniqueness,
      list, update; password hashing untouched (bcrypt) — assert it is not
      regressed by the refactor.
- [ ] **4. Keep auth behavior identical** — login/JWT issuance unchanged; this is a
      structural refactor + tests, not an auth change.

## Out of scope

- Bringing user-service under Alembic (debt §4 / repayment item 3) — separate work.
- WorkOS or any non-local auth — auth stays local JWT.

## Acceptance

- [ ] `UserRepository` owns user data access; service layer uses it.
- [ ] `services/user-service/tests/` exists; CI runs `pytest --cov` for it; suite green.
- [ ] Login/JWT behavior unchanged (regression-checked).
- [ ] `FEATURE_STATUS.md` row flipped to ✅ with evidence.
