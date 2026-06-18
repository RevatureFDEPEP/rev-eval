# W5-F4 — Auto-seed the question bank in Docker Compose — Plan

**Feature detail:** [docs/features/w5-f4-compose-question-bank-seed.md](../features/w5-f4-compose-question-bank-seed.md)
**Spec origin:** trainer-defined remediation; deferred from
[W3-F1](../features/w3-f1-quiz-session-backend.md) (line 78, "out of scope, unresolved").
**Depends on:** question-management-service, Mongo (both present & healthy).
**Unblocks:** a fresh `docker compose up` can mint sessions without manual seeding.

## Locked decisions

- **Trigger = guarded idempotent in-process startup seed** in
  question-management-service (the detail doc's *preferred* option), not a
  one-shot compose seeder service. Reasons: QMS already owns Beanie/Mongo init
  on startup; no extra container; the flag lives next to the service it gates.
- **Default-on for local dev, opt-out via env** (`SEED_QUESTION_BANK`, default
  `true`). Compose sets it explicitly; non-local profiles set it `false`.
- **Reuse the existing fixture data, do not duplicate or change it.** The 31
  questions in `seed_rag_context_questions.py` are the single source of truth.
  We *move* the `QUESTIONS` list into a pure-data module (no `httpx` import) so
  both the existing HTTP script and the new startup seeder import the same list.
  Fixture content is unchanged (out-of-scope per the detail doc).

## Context

- **Problem:** `POST /sessions` samples Mongo via `$sample`. On a clean stack the
  `questions` collection is empty, so `session_service` raises
  `EmptyQuestionBankError` → the session-create path fails until someone seeds by
  hand. Only the E2E CI job seeds (`scripts/e2e-seed.sh`, via `mongosh`).
- **Why the existing script can't just be run in-process:**
  `seed_rag_context_questions.py` POSTs over HTTP to a hard-coded Codespaces URL
  and imports `httpx`, which is **not** in the QMS production image
  (`requirements.txt` has no `httpx`; the e2e script's header notes this). So the
  module can't be imported inside the service.
- **Startup path:** `start.sh` waits for Mongo → `init_db()` → `exec python
  main.py`; `main.py`'s `@app.on_event("startup")` runs `init_db()` (initialises
  Beanie with the `Question` model) then `ensure_bucket()`. The seed hook belongs
  **after `init_db()`** in that startup event, where Beanie is live.
- **Reuse the create path, not raw inserts.** `QuestionService.create_question`
  takes a `QuestionCreate`, auto-generates 1-indexed `option_id`s, and validates
  per type. Routing the fixtures through it keeps option-id generation and
  validation identical to the API.
- **Known fixture defect (NOT in scope to fix here):** some `true_false`
  fixtures encode `correct_answers` as `[0]` / `[True]` / `[False]`;
  `QuestionCreate` requires a single `bool` for `true_false`, so `[0]` fails
  validation. The seeder must be **robust**: per-question try/except, log+skip a
  rejected fixture, continue. This is the W5-F3-flagged seed encoding defect —
  tracked separately, not changed here. With 31 fixtures, the bank still lands
  well-populated even if a couple of malformed true_false rows are skipped.
- **Idempotency / re-run safety:** seed only when the bank is empty
  (`count == 0`). A populated bank is left untouched, so `compose up` on an
  existing volume is a no-op. This also avoids duplicate inserts.
- **Gotchas honoured:** QMS uses Beanie/Motor over Mongo (no Alembic); compose
  service name is `question-management-service`; no gateway `ROUTES` change
  (this adds no routable endpoint).

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W5F4`** off `richardh` before any code change.
- **First commit on the branch = this plan file.**
- One commit per milestone, Conventional Commits.

## Milestones

### M1 — Extract fixtures into a no-httpx data module (reuse, no duplication)
- Add `services/question-management-service/src/db/seed_data.py` containing the
  `QUESTIONS: list[dict]` list **moved verbatim** from
  `seed_rag_context_questions.py` (content unchanged).
- Edit `seed_rag_context_questions.py` to `from src.db.seed_data import QUESTIONS`
  (drop its inline copy), leaving its HTTP behaviour intact.
- *Touches:* `src/db/seed_data.py` (new), `seed_rag_context_questions.py`.
- **Commit:** `refactor(qms): extract question fixtures to src/db/seed_data`.

### M2 — Idempotent, guarded startup seeder
- Add `services/question-management-service/src/db/seed.py` with
  `async def seed_question_bank() -> int`:
  - Return `0` immediately if `not settings.SEED_QUESTION_BANK`.
  - `count = await Question.find_all().count()`; if `count > 0`, log
    "bank already has N questions, skipping seed" and return `0`.
  - Else iterate `QUESTIONS`, build `QuestionCreate(**q)` and call
    `QuestionService.create_question` inside a per-item `try/except`
    (`ValidationError`/`HTTPException`/`Exception`): log a warning naming the
    skipped fixture, continue. Return the number successfully inserted; log the
    summary.
- Add `SEED_QUESTION_BANK: bool = True` to `src/config/settings.py`.
- *Touches:* `src/db/seed.py` (new), `src/config/settings.py`.
- **Commit:** `feat(qms): guarded idempotent question-bank startup seeder`.

### M3 — Wire seeder into startup + compose/env gating
- In `main.py` `on_startup`, after `await init_db()`, call
  `await seed_question_bank()` wrapped in try/except (non-fatal: a seed failure
  must not stop the service from serving), logging a warning on failure.
- In `docker-compose.yml` QMS `environment:` add
  `SEED_QUESTION_BANK: ${SEED_QUESTION_BANK:-true}`.
- In `.env.example` add `SEED_QUESTION_BANK=true` under the Mongo section with a
  one-line comment (default-on local; set `false` for prod-like profiles).
- *Touches:* `main.py`, `docker-compose.yml`, `.env.example`.
- **Commit:** `feat(qms): run question-bank seed on startup, gate via SEED_QUESTION_BANK`.

### M4 — Unit test (idempotency + guard)
- Add `services/question-management-service/tests/test_seed.py` using the
  existing `beanie_db` mongomock fixture:
  - seeding an empty bank inserts > 0 questions and is type-correct;
  - a second `seed_question_bank()` call is a no-op (count unchanged);
  - `SEED_QUESTION_BANK=false` inserts nothing.
- This also satisfies the Dockerfile `test` stage (`pytest -q`), so the in-image
  test gate covers the seeder.
- *Touches:* `tests/test_seed.py` (new).
- **Commit:** `test(qms): cover startup seeder idempotency and guard flag`.

### M5 — Requirements review + docs
- Re-read the detail-doc Steps + Acceptance against the diff; cite evidence.
- Update the detail doc (check off Steps 1–5, add evidence) and flip the
  `FEATURE_STATUS.md` W5-F4 row to ✅ with evidence.
- Add a `SEED_QUESTION_BANK` note to the CLAUDE.md seed section.
- *Touches:* `docs/features/w5-f4-compose-question-bank-seed.md`,
  `docs/FEATURE_STATUS.md`, `CLAUDE.md`.
- **Commit:** `docs(W5-F4): mark complete; document SEED_QUESTION_BANK flag`.

## Testing & validation

- **Unit:** from `services/question-management-service/`:
  `pytest -q` (and `pytest --cov` as CI does). Pass bar: all green, new
  `test_seed.py` included.
- **Build gate:** `docker build --target test
  services/question-management-service` runs `pytest -q` in-image — must pass.
- **Smoke (clean volume):**
  ```bash
  docker compose down -v
  docker compose up --build -d --wait
  # bank populated:
  curl -s localhost:8003/v1/api/questions/ | head
  # session mints (auth via gateway; or hit test-management-service directly):
  # POST /sessions for a seeded test → 200/201, not the empty-bank failure
  ```
  Pass bar: `questions` collection non-empty after a clean `up`; `POST /sessions`
  succeeds without a manual seed step. Re-running `compose up` does not duplicate.

## Push gate

Push `richardh-feat-W5F4` to origin **only if** unit tests pass **and** the
requirements review confirms every detail-doc Step + Acceptance item is met.
Otherwise stop and report what's outstanding.

## Out of scope (noted, not done here)

- Changing question fixtures or the `$sample` logic.
- Fixing the `true_false` `correct_answers` encoding defect (W5-F3-flagged;
  separate feature). The seeder tolerates it by skipping rejected rows.
