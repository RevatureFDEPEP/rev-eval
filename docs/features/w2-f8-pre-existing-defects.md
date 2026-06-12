# W2-F8 — Pre-Existing Defect Cleanup (found during W2-F7)

**Status:** ❌ Not Started
**Spec:** — (not a curriculum feature; defects surfaced while implementing
and verifying [W2-F7](w2-f7-alembic-category-domain.md))
**Last updated:** 2026-06-12

Fix pre-existing bugs surfaced during Week 2 implementation.

## Items

- [ ] **1. Gateway 500 on bodyless responses** — `NextResponse.json(null, {204})`
      in the BFF causes a gateway DELETE (204) to surface as 500; fix the
      BFF to pass bodyless 204/205 through unchanged.
- [ ] **2. `GET /skills/{skill_id}/` always 500s** — diagnose and fix the
      skill lookup endpoint.
- [ ] **3. user-service dual engine** — user-service has two engines and a
      tangled db module pair; consolidate to a single engine instance.
- [ ] **4. Pydantic v2 deprecations** — migrate `orm_mode`, `validator`, and
      other v1 patterns to v2 equivalents across all services.

## Evidence

None on `tianyac` branch.

Note: another contributor fixed these on branch `richardh-feat-w2f8`
(commits `1fac5ba`, `da1f5cc`, `396f34d`); that work is not yet merged into
`tianyac`.

## Remaining

All items. Naturally surfaces during [W2-F7](w2-f7-alembic-category-domain.md)
verification.
