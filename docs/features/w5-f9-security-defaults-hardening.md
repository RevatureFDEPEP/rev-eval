# W5-F9 — Security defaults hardening (JWT / CORS / MinIO / presign)

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin:
[technical-debt.md](../technical-debt.md) §1; **repayment backlog items 1 & 2**
(the two highest-urgency items in the inventory).
**Depends on:** none.
**Unblocks:** safe-by-default posture the moment the platform leaves local dev.
**Last updated:** 2026-06-17

## Problem

The platform ships insecure defaults that are fine behind the local gateway but a
liability on any non-local origin:

- **`JWT_SECRET = "change-me-in-production"`** (high) — user-service *issues* and
  reporting *verifies* with it; a non-local deploy that forgets to set it makes
  every JWT forgeable (anyone mints a TRAINER token).
  `services/user-service/src/config/settings.py:21`,
  `services/reporting-and-analytics-service/src/config/settings.py:25`, `.env.example`.
- **CORS `allow_origins = ["*"]`** (high) — wildcard with credentials on a public
  origin lets any site make credentialed cross-origin calls.
  `services/user-service/src/config/settings.py:14` & `main.py:24-28`;
  `reporting-and-analytics-service/src/config/settings.py:33`;
  `question-management-service/src/config/settings.py:25`; test-management `main.py`.
- **MinIO creds `minioadmin`/`minioadmin`** (med) — well-known default; exposed
  MinIO is fully read/write. `question-management-service/src/config/settings.py:38-39`.
- **Presign expiry magic `3600`** (low) — hardcoded 1h, not tunable.
  `question-management-service/src/config/settings.py` (`S3_PRESIGN_EXPIRY_SECONDS`).

## Steps

- [ ] **1. `JWT_SECRET` fail-fast** — for any non-local profile, refuse to start
      (no default fallback) if `JWT_SECRET` is unset/equals the placeholder. Keep
      user-service and reporting in sync (same secret). Local-dev keeps a convenient
      default via an explicit `APP_ENV=local`-style gate.
- [ ] **2. CORS closed-by-default** — default `allow_origins` to a closed/empty set;
      open per-env via config across all four services + the gateway.
- [ ] **3. MinIO creds off the shipped default** — require non-default creds for
      non-local; document rotation in `.env.example`.
- [ ] **4. Presign expiry to config** — make `S3_PRESIGN_EXPIRY_SECONDS` env-driven
      with a sane default (folds the §1-low magic number in here).
- [ ] **5. Tests** — startup fails when `JWT_SECRET` missing on a non-local profile;
      CORS default rejects an unlisted origin; local profile still boots with defaults.
- [ ] **6. Docs** — `.env.example` + CLAUDE.md note the required-for-non-local vars.

## Out of scope

- Secret-manager integration / rotation automation — fail-fast + per-env config only.

## Acceptance

- [ ] No forgeable-JWT or wildcard-CORS default reachable on a non-local profile;
      local dev unaffected.
- [ ] Tests green; `FEATURE_STATUS.md` row ✅; debt §1 / repayment 1–2 cross-referenced.
