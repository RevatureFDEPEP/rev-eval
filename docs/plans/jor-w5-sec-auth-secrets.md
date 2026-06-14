# Claude Execution Prompt — Week 5 Security AuthZ and Secrets Hardening

## Target Branch

`jor-w5-sec-auth-secrets`

## Plan Document

Use this plan as the starting point:

`docs/plans/fix/security-authz-and-secrets.md`

## Mission

Analyze, validate, and implement the Week 5 security hardening work for authorization, authentication, secrets, gateway routing, login throttling, infrastructure exposure, and Nginx TLS/header hardening.

This is a **RED / P0 security branch**. The goal is to close privilege-escalation, unauthenticated-enumeration, IDOR, weak-JWT, unsafe-secret, and exposed-infrastructure risks without breaking existing application behavior.

Do not blindly apply the plan. First inspect the current repo state, confirm which findings are still valid, identify exact files/routes/tests affected, and modify the plan if the current code differs from the assumptions.

---

## Permission Model

You have broad permission to inspect, analyze, create the branch, add tests, update documentation, and make normal implementation changes after approval to begin coding.

Before coding, do the following:

1. Inspect the repository.
2. Validate the findings in this plan.
3. Report what is confirmed, partially confirmed, not found, or already fixed.
4. Propose the exact first implementation slice.
5. Ask for permission to begin coding and create the new branch.

Use this wording before coding:

> I validated the current repo state and found the issues below. I recommend beginning with `[first slice]`. May I create branch `jor-w5-sec-auth-secrets` and begin coding?

After permission is granted, create the branch and begin.

Ask again only before modifying **critical code paths** where the change could significantly alter authentication flow, token compatibility, database schema, production runtime behavior, or public API contracts.

Do **not** ask for permission for routine test additions, documentation updates, small helper functions, route dependency additions, or normal refactors needed to complete the approved slice.

---

## Pre-Coding Validation Steps

Run these checks before creating the branch:

```bash
git status
git branch --show-current
git fetch origin
git log --oneline --decorate -5
git branch -vv
```

Confirm that the working tree is clean. If not clean, stop and report the changed files before making changes.

Then inspect the likely target files:

```bash
ls
find services -maxdepth 4 -type f | sort | sed -n '1,200p'

sed -n '1,240p' services/api-gateway-service/main.py
sed -n '1,240p' services/api-gateway-service/src/middleware/auth.py

sed -n '1,260p' services/user-service/src/v1/routes/user_route.py
sed -n '1,260p' services/user-service/src/utils/dependencies.py
sed -n '1,260p' services/user-service/src/services/auth_service.py

sed -n '1,300p' services/test-management-service/src/utils/dependencies.py
sed -n '1,300p' services/test-management-service/src/v1/routes/test_route.py
sed -n '1,300p' services/test-management-service/src/v1/routes/skill_route.py
sed -n '1,360p' services/test-management-service/src/v1/routes/test_submission_route.py

sed -n '1,260p' docker-compose.yml
sed -n '1,260p' nginx/nginx.conf
sed -n '1,220p' .env.example
```

If file paths differ, search instead:

```bash
grep -R "legacy_gateway\|X-User\|JWT_SECRET\|change-me-in-production\|decode" -n services nginx docker-compose.yml .env.example
grep -R "APIRouter\|router.patch\|router.post\|router.put\|router.delete" -n services/user-service services/test-management-service
grep -R "submission_id\|user_id" -n services/test-management-service/src
```

---

## Required Analysis Output Before Coding

Report findings in this format:

```md
## Security validation report

### Confirmed
- [ ] Issue:
  - Evidence:
  - Risk:
  - Proposed fix:
  - Files likely changed:

### Partially confirmed / needs adjustment
- [ ] Issue:
  - What differs from the plan:
  - Safer revised approach:

### Not found / already fixed
- [ ] Issue:
  - Evidence:
  - No code change needed, or remaining documentation/test needed:

### Recommended first coding slice
Start with:
1. ...
2. ...
3. ...

May I create branch `jor-w5-sec-auth-secrets` and begin coding?
```

---

## Branch Creation After Approval

After approval:

```bash
git switch jorge-main
git pull --ff-only origin jorge-main
git switch -c jor-w5-sec-auth-secrets
git status
```

If `jorge-main` is not the correct base branch, stop and report the current branches before creating the new branch.

---

# Implementation Plan

## Phase 1 — User-Service Authorization Boundary

### Goal

Prevent user enumeration, privilege escalation, unauthorized profile mutation, and role/status tampering.

### Validate

Inspect:

* `services/user-service/src/v1/routes/user_route.py`
* `services/user-service/src/utils/dependencies.py`
* `services/user-service/src/services/auth_service.py`
* user schemas/models for fields such as `role`, `is_active`, `email`, `name`, and profile fields

### Required Fixes

1. Add or improve dependencies:

   * `get_current_admin`
   * `get_current_admin_or_self`
   * role normalization helper
   * safe current-user extraction

2. Protect user routes:

   * `/users/` list: admin only
   * `/users/invite`: admin only
   * `/users/by-email`: admin only unless strictly internal and otherwise protected
   * `/users/{user_id}` read: admin or self
   * `PATCH /users/{user_id}`: admin or self

3. Add field-level authorization:

   * self-user update may change only safe profile fields
   * self-user update may not change:

     * `role`
     * `is_active`
     * privileged/admin-only fields
   * admin may update privileged fields when business logic allows

### Tests

Add or update tests for:

* anonymous user cannot list users
* participant cannot list users
* participant cannot read another user
* participant can read self
* participant cannot update another user
* participant cannot change own role or `is_active`
* admin can list users
* admin can invite users
* admin can update role/status if supported

### Commit Suggestion

```bash
git add services/user-service
git commit -m "fix(user): enforce user authorization boundaries"
```

---

## Phase 2 — API Gateway Legacy Route and Header Spoofing Hardening

### Goal

Remove or protect unauthenticated service-name routing and ensure client-supplied identity headers cannot be trusted.

### Validate

Inspect:

* `services/api-gateway-service/main.py`
* `services/api-gateway-service/src/middleware/auth.py`
* gateway tests
* any frontend or service caller that still uses `/{service}/{path}` directly

### Preferred Fix

Remove the legacy route if it is not required.

### Acceptable Compatibility Fix

If removal breaks known current behavior, keep the legacy route only if it has:

* `Depends(verify_jwt_token)`
* strict service/path allowlist
* same verified user-context header injection as the primary smart route
* inbound identity header stripping before proxying

### Header-Spoofing Requirements

Strip or overwrite inbound:

* `X-User-Id`
* `X-User-Email`
* `X-User-Role`
* any related identity headers

Only gateway-created values from verified JWT claims should reach downstream services.

### Tests

Add or update tests for:

* unauthenticated legacy route returns `404`, `410`, or `401`
* spoofed `X-User-Role: ADMIN` is ignored/replaced
* missing/invalid JWT does not reach protected downstream routes
* valid JWT injects expected verified headers

### Commit Suggestion

```bash
git add services/api-gateway-service
git commit -m "fix(gateway): protect legacy routing and identity headers"
```

---

## Phase 3 — Test-Management Authorization and Submission IDOR Guards

### Goal

Protect test, skill, and submission write routes. Prevent participants and trainers from accessing or mutating submissions they do not own or manage.

### Validate

Inspect:

* `services/test-management-service/src/utils/dependencies.py`
* `services/test-management-service/src/v1/routes/test_route.py`
* `services/test-management-service/src/v1/routes/skill_route.py`
* `services/test-management-service/src/v1/routes/test_submission_route.py`
* repository/query helpers for submissions/tests
* models relating submissions to participants, tests, creators, trainers, reviewers, or assignments

### Required Fixes

1. Centralize role dependencies:

   * `get_current_trainer_or_admin`
   * `get_current_admin`
   * `require_role`
   * helper for participant/self ownership checks

2. Protect test routes:

   * create/update/delete require trainer/admin
   * trainer edits should respect creator ownership unless admin
   * participant routes should not use broad management endpoints

3. Protect skill routes:

   * read/list can remain read-only if product intent allows
   * create/update/delete require trainer/admin or admin-only

4. Protect submission routes:

   * participants can only read their own submissions
   * participants cannot pass `?user_id=other` to view another user’s submissions
   * trainer can review only submissions tied to tests they own/manage
   * admin can cross ownership boundaries
   * direct status/score mutation must be restricted to trainer/admin workflows
   * delete/update should not be available to participants unless explicitly designed and safe

5. Add repository helpers if needed:

   * fetch submission with related test
   * verify participant ownership
   * verify trainer ownership through test creator/assignment relationship

### Tests

Add or update tests for:

* anonymous direct service request receives `401`
* participant cannot create/update/delete tests
* participant cannot create/update/delete skills
* participant cannot fetch another participant’s submission by ID
* participant cannot bypass ownership using `?user_id=other`
* trainer cannot review another trainer’s submission
* trainer can review assigned/owned submission
* admin can perform cross-owner operation
* authorized happy paths still work

### Commit Suggestion

```bash
git add services/test-management-service
git commit -m "fix(test-mgmt): enforce route authz and submission ownership"
```

---

## Phase 4 — JWT Claim and Secret Hardening

### Goal

Strengthen token issuance and validation. Prevent role-less tokens, wrong-audience tokens, wrong-issuer tokens, future/not-yet-valid tokens, and unsafe secrets from being accepted.

### Validate

Inspect:

* token creation in user-service
* token verification in gateway
* token verification in downstream services
* environment settings
* tests that mint JWTs manually
* compose and `.env.example`

### Required JWT Claims

Issued tokens should include:

* `sub`
* `email`
* `role`
* `iss`
* `aud`
* `iat`
* `nbf`
* `exp`

Validation should require:

* valid signature
* expected algorithm
* expiration
* issuer
* audience
* not-before
* subject
* role
* known role value

### Required Settings

Add or standardize:

* `JWT_SECRET`
* `JWT_ISSUER`
* `JWT_AUDIENCE`
* `JWT_MIN_SECRET_LENGTH`
* `ALLOW_INSECURE_DEV_SECRETS`

### Secret Hardening

Fail fast if `JWT_SECRET` is:

* missing
* empty
* `change-me-in-production`
* obvious placeholder
* too short
* accepted through unsafe fallback in non-local mode

Use an explicit local-dev escape hatch only if needed:

```env
ALLOW_INSECURE_DEV_SECRETS=true
```

Do not silently accept insecure defaults.

### Tests

Add or update tests for:

* missing role rejected
* unknown role rejected
* wrong issuer rejected
* wrong audience rejected
* future `nbf` rejected
* expired token rejected
* default/short secret rejected under secure mode
* valid token still accepted

### Commit Suggestion

```bash
git add services docker-compose.yml .env.example
git commit -m "fix(auth): require strong JWT claims and secrets"
```

---

## Phase 5 — Login Rate Limiting and Nginx TLS/Header Hardening

### Goal

Reduce brute-force login risk and improve browser/API edge security.

### Validate

Inspect:

* `nginx/nginx.conf`
* current auth/login route path after rewrites
* frontend/API path structure
* local TLS config

### Required Fixes

1. Add login rate limit zone:

```nginx
limit_req_zone $binary_remote_addr zone=auth_login:10m rate=5r/m;
```

2. Apply to login route only, or as narrowly as possible:

```nginx
limit_req zone=auth_login burst=5 nodelay;
```

3. Return `429` for excessive attempts.

4. Add TLS/security headers when compatible:

* `Strict-Transport-Security`
* `X-Content-Type-Options`
* `Referrer-Policy`
* `X-Frame-Options` or CSP frame policy
* carefully test any `Content-Security-Policy` with Next.js assets before committing

5. Add proxy safety defaults:

* body size limit where appropriate
* proxy timeouts
* trusted forwarded header normalization

### Tests / Verification

Run:

```bash
docker compose config
docker compose exec nginx nginx -t
```

Manual verification:

```bash
curl -k -i https://localhost/api/v1/api/auth/login
```

If rate-limit testing is practical, run a short burst and confirm `429`.

### Commit Suggestion

```bash
git add nginx docker-compose.yml
git commit -m "fix(nginx): harden login throttling and TLS headers"
```

---

## Phase 6 — Compose Exposure and Default Credential Hardening

### Goal

Reduce accidental LAN exposure and remove unsafe default credentials.

### Validate

Inspect:

* `docker-compose.yml`
* `.env.example`
* README or local setup docs
* which ports are intentionally public for local development

### Required Fixes

Bind internal/local-only services to loopback where host access is needed:

```yaml
127.0.0.1:5432:5432
127.0.0.1:27017:27017
127.0.0.1:9000:9000
127.0.0.1:9001:9001
```

Apply the same pattern to observability ports unless intentionally shared:

* Grafana
* Loki
* Alloy/Promtail
* any internal service debug ports

Keep Nginx as the intended browser/public ingress.

Remove unsafe runtime fallbacks where practical:

* `root/root`
* `admin/admin`
* `minioadmin/minioadmin`
* `change-me-in-production`
* Grafana `admin/admin`

Use placeholders or documented local generation instead.

### Verification

```bash
docker compose config
docker compose ps
```

Optional Windows/Git Bash checks:

```bash
netstat -ano | findstr ":5432"
netstat -ano | findstr ":27017"
```

### Commit Suggestion

```bash
git add docker-compose.yml .env.example README.md docs
git commit -m "fix(infra): restrict local ports and unsafe defaults"
```

---

# Final Verification

Run the most relevant tests first:

```bash
pytest services/user-service/tests
pytest services/api-gateway-service/tests
pytest services/test-management-service/tests
```

Then run broader verification if available:

```bash
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Smoke checks:

```bash
curl -i http://localhost:8000/v1/api/users/
curl -i http://localhost:8000/user-service/v1/api/users/
curl -i "http://localhost:8000/v1/api/submissions?user_id=2" -H "Authorization: Bearer <participant-token>"
```

Expected results:

* unauthenticated protected routes return `401`
* unauthorized role access returns `403`
* removed legacy route returns `404` or `410`
* retained legacy route requires JWT
* spoofed `X-User-*` headers do not grant privileges
* valid admin/trainer/participant paths still work according to role
* docker compose config is valid
* Nginx config validates

---

# Documentation Updates

Update or create:

```text
docs/plans/fix/security-authz-and-secrets.md
```

Include:

* confirmed findings
* final implementation decisions
* changed files
* security behavior before/after
* test commands and results
* any intentionally deferred items

---

# PR Preparation

Before opening the PR:

```bash
git status
git diff --stat origin/jorge-main...HEAD
git log --oneline origin/jorge-main..HEAD
```

Suggested PR title:

```text
fix(security): harden authz, JWT secrets, and gateway routing
```

Suggested PR summary:

```md
## Summary

This PR closes P0 security gaps across user authorization, gateway routing, JWT validation, test-management ownership checks, login throttling, and local infrastructure exposure.

## Key changes

- Enforced admin/self authorization for user reads and updates.
- Blocked user privilege escalation through role/status mutation.
- Removed or protected legacy gateway routing.
- Stripped/replaced spoofable identity headers.
- Added route-level authorization for test, skill, and submission mutation paths.
- Added submission ownership checks to prevent IDOR.
- Strengthened JWT issuance and validation with issuer, audience, nbf, iat, exp, and required role claims.
- Failed fast on unsafe JWT secrets/defaults.
- Added Nginx login rate limiting and TLS/security headers.
- Restricted local infrastructure ports to loopback where appropriate.

## Validation

- [ ] `pytest services/user-service/tests`
- [ ] `pytest services/api-gateway-service/tests`
- [ ] `pytest services/test-management-service/tests`
- [ ] `docker compose config`
- [ ] `docker compose exec nginx nginx -t`
- [ ] Manual auth smoke checks completed

## Notes

This branch intentionally keeps asymmetric JWT signing, production WAF policy, and deeper account-lockout/audit workflows out of scope unless required by review.
```

---

# Safety Rules While Implementing

* Do not weaken existing authentication to make tests pass.
* Do not trust frontend-only authorization.
* Do not trust client-supplied `X-User-*` headers.
* Do not silently accept default JWT secrets.
* Do not expose internal services broadly unless explicitly justified.
* Prefer explicit `401` for unauthenticated and `403` for authenticated-but-unauthorized.
* Preserve existing happy paths where they are secure.
* Add regression tests for every security fix.
