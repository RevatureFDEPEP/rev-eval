# W5-F4 — Auto-seed the question bank in Docker Compose

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: deferred from
[W3-F1](w3-f1-quiz-session-backend.md) (line 78, "out of scope, unresolved").
**Depends on:** question-management-service, Mongo.
**Unblocks:** a fresh `docker compose up` can mint sessions without manual seeding.
**Last updated:** 2026-06-17

## Problem

`POST /sessions` samples the Mongo question bank via `$sample`. On a fresh stack
the bank is **empty**, so session creation fails (422 / short-fill) until someone
runs a seed script by hand. There is an idempotent seeder
(`scripts/e2e-seed.sh`, `services/question-management-service/seed_rag_context_questions.py`)
but `docker compose up` does not run it — only the E2E CI job does.

## Steps

- [ ] **1. Decide the seed trigger** — preferred: a guarded, idempotent startup
      seed in question-management-service (only when the bank is empty and a
      `SEED_QUESTION_BANK`-style flag is on), so prod-like profiles can opt out.
      Alternative: a one-shot compose seeder service depending on `mongo`.
- [ ] **2. Implement** the chosen trigger; reuse the existing seed data/script —
      do not duplicate question fixtures. Make it safe to re-run (no duplicates).
- [ ] **3. Default-on for local dev, opt-out for non-local** — gate via env so the
      behavior matches the platform's local-first stance without forcing seed data
      into a real deployment.
- [ ] **4. Verify** — `docker compose up --build` on a clean volume → bank
      populated → `POST /sessions` succeeds end-to-end (smoke).
- [ ] **5. Docs** — note the flag in `.env.example` and CLAUDE.md's seed section.

## Out of scope

- Changing the question fixtures themselves or the `$sample` logic.

## Acceptance

- [ ] Clean `docker compose up` yields a non-empty bank and a successful
      `POST /sessions` without a manual seed step.
- [ ] Seeding is idempotent and opt-out-able for non-local profiles.
- [ ] `FEATURE_STATUS.md` row flipped to ✅ with evidence.
