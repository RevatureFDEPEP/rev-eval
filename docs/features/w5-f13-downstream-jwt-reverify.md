# W5-F13 — Harden the auth boundary (downstream JWT re-verify)

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin:
[technical-debt.md](../technical-debt.md) §6; **repayment backlog item 5**.
**Depends on:** W4-F3 established the pattern (reporting service re-verifies).
**Unblocks:** defense-in-depth if any service is reachable past the gateway.
**Last updated:** 2026-06-17

## Problem

Downstream services trust `X-User-Id/Email/Role` injected by the gateway **without
re-verifying the JWT**. The gateway is the sole auth boundary — if any service is
reachable directly (misconfigured network, exposed port), a spoofed
`X-User-Role: TRAINER` header is trusted.

```
gateway injects: services/api-gateway-service/main.py
consumed (no re-verify) by: test-management-service, user-service, question-management-service
```

The reporting service is the lone exception — it re-verifies the JWT itself (W4-F3
defense-in-depth, `require_trainer`/python-jose + shared `JWT_SECRET`). That is the
pattern the others should adopt. (Coordinate with [W5-F9](w5-f9-security-defaults-hardening.md):
re-verify needs a real, in-sync `JWT_SECRET`.)

## Steps

- [ ] **1. Choose the mechanism** — preferred: lift W4-F3's JWT re-verify dependency
      into a shared/duplicated `auth` dependency and apply it on the protected routes
      of test-management, user, and question services; derive `X-User-*` from the
      *verified* claims rather than trusting raw headers. Alternative (or additional):
      lock down direct reachability (network policy / not exposing service ports).
- [ ] **2. Apply incrementally, service by service** — start with the most
      sensitive reads/writes; keep the gateway's header injection working for
      internal/headerless calls that legitimately bypass auth (e.g. the TMS→QMS
      sampler) per existing W3-F7 item-4 carve-outs.
- [ ] **3. Tests** — direct-to-service curl with a spoofed `X-User-Role` and no/invalid
      JWT → 401/403; valid token → 200. Mirror W4-F3's gate matrix.
- [ ] **4. Docs/ADR** — record the boundary decision (extend ADR set or technical
      narrative); update CLAUDE.md's "downstream trust" gotcha once closed.

## Out of scope

- Replacing the gateway routing model — this adds depth behind it, not a redesign.

## Acceptance

- [ ] Protected downstream routes reject spoofed-header / unauthenticated direct
      calls; gateway path + legitimate headerless internal calls still work.
- [ ] Tests green; `FEATURE_STATUS.md` row ✅; debt §6 / repayment 5 cross-referenced.
