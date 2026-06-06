# F8 — Pre-Existing Defect Cleanup (found during F7)

**Status:** 🟡 In Progress
**Spec:** — (not a curriculum feature; defects surfaced while implementing
and verifying [F7](f7-alembic-category-domain.md) on branch
`richardh-feat-alembic`)
**Last updated:** 2026-06-05

Defects that predate F7, discovered while mirroring the Skill vertical slice
and running the full stack through the gateway. Tracked here so they get
fixed deliberately instead of rediscovered one 500 at a time.

## Steps

- [x] **1. Gateway 500 on bodyless responses** — the gateway called
      `resp.json()` on every `application/json` response, but 204 No Content
      replies carry that content-type with an empty body, so **every
      successful DELETE through the gateway returned 500** (service-side
      delete still happened — clients saw an error for an operation that
      succeeded). Fixed in F7: both proxy paths in
      `services/api-gateway-service/main.py` now short-circuit when
      `resp.content` is empty. Evidence: commit `cfac9ce`, verified live
      (unlink/delete = 204 through the gateway).
- [ ] **2. `GET /skills/{skill_id}/` always 500s** —
      `src/v1/routes/skill_route.py` calls `SkillService.get_skill_by_id`,
      but `src/services/skill_service.py` never defines it → `AttributeError`
      at request time. Fix: add `get_skill_by_id` (repo `get_by_id`,
      `ValueError` on miss → route 404), mirroring
      `CategoryService.get_category_by_id`. Add a unit test — the route has
      clearly never been exercised.
- [ ] **3. user-service has two engines and a tangled db module pair** —
      `src/db/init_db.py` builds its own `engine` (with `echo=True`),
      `SessionLocal`, and `get_db`, none of which the app uses; it only
      "lends" `Base` to `src/db/session.py`, which builds a second engine and
      imports `User` at module scope (the import-order trap documented in
      `conftest.py`). Fix: collapse to one module — `Base` plus a single
      engine/session in `session.py`, delete the dead engine in `init_db.py`
      (or the file), and drop the circular-import workaround.
- [ ] **4. Pydantic v2 deprecations across services** — every pytest run
      warns: class-based `class Config` (e.g.
      `src/config/settings.py`, `src/schemas/*` in user- and
      test-management-service) and `.from_orm()` / `.copy()` throughout
      `test_service.py` and `skill_service.py`. All removed in Pydantic v3.
      Fix: `model_config = ConfigDict(...)`, `model_validate()`,
      `model_copy()`. New F7 code already uses `model_validate` —
      use it as the pattern.

## Notes

- Item 1 was fixed inside the F7 branch because F7's verification could not
  pass without it; the rest are untouched to keep F7 reviewable.
- Items 2–4 are well-shaped candidate tasks: small blast radius, each
  teaches something (route/service contract testing, engine lifecycle,
  Pydantic v2 migration).
- When fixing item 2, sweep the other routes for the same
  route-calls-missing-service-method shape before closing.

## Remaining

Items 2–4.
