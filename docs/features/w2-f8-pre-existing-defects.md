# W2-F8 — Pre-Existing Defect Cleanup (found during W2-F7)

**Status:** ✅ Completed
**Spec:** — (not a curriculum feature; defects surfaced while implementing
and verifying [W2-F7](w2-f7-alembic-category-domain.md) on branch
`richardh-feat-alembic`)
**Last updated:** 2026-06-08
**Implemented on:** branch `richardh-feat-w2f8` (commits `1fac5ba`, `da1f5cc`, `396f34d`)
**Plan:** [`docs/plans/w2-f8-defect-cleanup.md`](../plans/w2-f8-defect-cleanup.md)

Defects that predate W2-F7, discovered while mirroring the Skill vertical slice
and running the full stack through the gateway. Tracked here so they get
fixed deliberately instead of rediscovered one 500 at a time.

## Steps

- [x] **1. Gateway 500 on bodyless responses** — the gateway called
      `resp.json()` on every `application/json` response, but 204 No Content
      replies carry that content-type with an empty body, so **every
      successful DELETE through the gateway returned 500** (service-side
      delete still happened — clients saw an error for an operation that
      succeeded). Fixed in W2-F7: both proxy paths in
      `services/api-gateway-service/main.py` now short-circuit when
      `resp.content` is empty. Evidence: commit `cfac9ce`, verified live
      (unlink/delete = 204 through the gateway).
- [x] **2. `GET /skills/{skill_id}/` always 500s** —
      `src/v1/routes/skill_route.py` calls `SkillService.get_skill_by_id`,
      but `src/services/skill_service.py` never defined it → `AttributeError`
      at request time. **Fixed:** added `get_skill_by_id` (repo `get_by_id`,
      `ValueError` on miss → route 404), mirroring
      `CategoryService.get_category_by_id`; converted the file's other
      `SkillOut.from_orm` calls to `model_validate`. New unit test
      `tests/test_skill_service.py` (4 cases: hit, miss→ValueError, create,
      list). Evidence: commit `1fac5ba`; tms suite 38 passed.
      **Route sweep:** audited every `test-management-service` route against
      its service methods — `skill_route.get_skill` was the **only**
      route-calls-missing-method mismatch. No further missing methods.
- [x] **3. user-service has two engines and a tangled db module pair** —
      `src/db/init_db.py` built its own `engine` (`echo=True`), `SessionLocal`,
      and `get_db`, none used by the app; it only "lent" `Base` to
      `src/db/session.py`, which built a second engine and imported `User` at
      module scope (the import-order trap in `conftest.py`). **Fixed:** `Base`
      now defined in `session.py`; the model registers via a deferred
      `from src.models import user` inside `init_db()` (no module-level cycle);
      deleted `init_db.py`; dropped the `conftest.py` preload workaround and
      pointed its fixture at `session.py`. Imports now resolve in any order
      (verified both `models`-first and `session`-first). Evidence: commit
      `da1f5cc`; user-service suite 22 passed.
- [x] **4. Pydantic v2 deprecations across services** — class-based
      `class Config`, `.from_orm()`, `.copy()`, and `.dict()` warned on every
      pytest run. **Fixed** across user-service, test-management-service, and
      **question-management-service** (per user decision to include qms):
      `class Config` → `model_config = ConfigDict(...)` (schemas) /
      `SettingsConfigDict(...)` (settings); `.from_orm()` → `model_validate()`;
      `.copy(update=)` → `model_copy(update=)`; `.dict()` → `model_dump()`,
      dropping the `hasattr(x,'model_dump')` v1/v2 shims. In qms the Beanie
      `Question.json_schema_extra` and `QuestionResponse.populate_by_name`
      moved onto `ConfigDict`; the deprecated
      `json_encoders={datetime: isoformat}` was dropped (v2 json mode already
      emits ISO 8601 — output verified byte-identical). Evidence: commit
      `396f34d`; suites: tms 38, user 22, qms 30 passed.
      **Residual:** 2 `PydanticDeprecatedSince211` `model_fields` warnings in
      the qms test run originate in `beanie`/`lazy_model` internals
      (site-packages), not this codebase. No app-code `PydanticDeprecatedSince20`
      warnings remain. Pinning `pydantic>=2,<3` was left as optional hardening
      (not applied — needs sign-off).

## Notes

- Item 1 was fixed inside the W2-F7 branch because W2-F7's verification could not
  pass without it; the rest are untouched to keep W2-F7 reviewable.
- Items 2–4 are well-shaped candidate tasks: small blast radius, each
  teaches something (route/service contract testing, engine lifecycle,
  Pydantic v2 migration).
- When fixing item 2, sweep the other routes for the same
  route-calls-missing-service-method shape before closing.

## Remaining

None — all items (1–4) closed.
