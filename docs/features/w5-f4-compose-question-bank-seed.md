# W5-F4 — Auto-seed the question bank in Docker Compose

**Status:** ✅ Completed
**Spec:** trainer-defined remediation (non-catalog). Origin: deferred from
[W3-F1](w3-f1-quiz-session-backend.md) (line 78, "out of scope, unresolved").
**Depends on:** question-management-service, Mongo.
**Unblocks:** a fresh `docker compose up` can mint sessions without manual seeding.
**Last updated:** 2026-06-18

## Problem

`POST /sessions` samples the Mongo question bank via `$sample`. On a fresh stack
the bank is **empty**, so session creation fails (422 / short-fill) until someone
runs a seed script by hand. There is an idempotent seeder
(`scripts/e2e-seed.sh`, `services/question-management-service/seed_rag_context_questions.py`)
but `docker compose up` does not run it — only the E2E CI job does.

## Steps

- [x] **1. Decide the seed trigger** — chose the preferred option: a guarded,
      idempotent startup seed in question-management-service, gated by
      `SEED_QUESTION_BANK` (not a one-shot compose service).
      Evidence: `services/question-management-service/src/db/seed.py:seed_question_bank`,
      plan `docs/plans/w5-f4-compose-question-bank-seed.md`.
- [x] **2. Implement** — `seed_question_bank()` reuses the existing fixtures via
      the new pure-data module
      `services/question-management-service/src/db/seed_data.py` (the 31-question
      list moved verbatim out of `seed_rag_context_questions.py`, which now
      imports it — no
      duplication). Validates each fixture via `QuestionCreate` and inserts
      through `QuestionRepository.create` (option_id generation mirrored in
      `_to_question`, keeping the seeder's imports minimal so it doesn't pull
      the service layer into the coverage gate); idempotent: only runs when
      `Question.find_all().count() == 0`, so re-runs insert nothing.
      Evidence: `services/question-management-service/src/db/seed.py`,
      `services/question-management-service/src/db/seed_data.py`,
      `services/question-management-service/seed_rag_context_questions.py:24`.
- [x] **3. Default-on for local dev, opt-out for non-local** — `SEED_QUESTION_BANK`
      defaults `True` (`services/question-management-service/src/config/settings.py`),
      set on the compose QMS service as `${SEED_QUESTION_BANK:-true}`
      (`docker-compose.yml`); set `false` to opt out.
      Evidence: `services/question-management-service/src/config/settings.py`
      (SEED_QUESTION_BANK), `docker-compose.yml` (QMS `environment`).
- [x] **4. Verify** — clean-DB smoke: ran the built QMS image against a fresh
      Mongo → startup log `Question bank empty; seeding 31 demo question(s)` →
      `seed complete: inserted=28 skipped=3` → `GET /v1/api/questions/` returned
      28 items; an immediate re-run inserted 0 (idempotent). 3 fixtures are
      rejected by `QuestionCreate` (0-indexed `correct_answers` / non-bool
      `true_false` — the W5-F3-flagged encoding defect) and skipped non-fatally,
      exactly as the existing HTTP script would. A non-empty bank satisfies
      `POST /sessions` (which only fails on `EmptyQuestionBankError`).
- [x] **5. Docs** — `.env.example` documents `SEED_QUESTION_BANK=true`;
      CLAUDE.md's seed section notes the startup auto-seed + flag.

## Out of scope

- Changing the question fixtures themselves or the `$sample` logic.
- Fixing the fixture `correct_answers` index/`true_false` encoding defect
  (0-indexed values rejected by the 1-indexed `QuestionCreate`). Pre-existing,
  W5-F3-flagged; tracked separately. The seeder tolerates it by skipping the
  3 affected rows (28/31 still seed).

## Acceptance

- [x] Clean `docker compose up` yields a non-empty bank (28 questions) and a
      `POST /sessions` that no longer hits the empty-bank failure — no manual
      seed step. Verified via the built QMS image on a fresh Mongo volume.
- [x] Seeding is idempotent (re-run inserts 0) and opt-out-able via
      `SEED_QUESTION_BANK=false`. Covered by
      `services/question-management-service/tests/test_seed.py` (3 tests).
- [x] `FEATURE_STATUS.md` row flipped to ✅ with evidence.
