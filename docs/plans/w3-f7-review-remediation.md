# W3-F7 — Week-3 Review-Findings Remediation

**Feature:** [w3-f7-review-remediation.md](../features/w3-f7-review-remediation.md)
(trainer-defined, non-catalog; source = code review of merged Week-3 PRs #72/#74/#75/#76).
**Depends on:** W3-F1..F4 merged (all are). **Unblocks:** W3-F4 completion
(item 1 is its acceptance blocker), W3-F6 (E2E must not freeze a broken timer),
W4-F3 (item 4 previews API-layer authorization).

Locked decisions:

- **Item 3 semantic = (a) reuse** — `POST /sessions` returns the existing ACTIVE
  session for `(user_id, test_id)` instead of minting a duplicate; the feature
  doc itself recommends (a) for candidate UX + free refresh-recovery.
- **Item 4 guard placement** — in question-management-service, one guard clause
  on `/sample`. Gateway always **overwrites** `X-User-Role` from the verified JWT
  (`services/api-gateway-service/src/middleware/auth.py:83-89`), so via the
  gateway the header is always the real role; test-management-service's internal
  `question_client.sample_questions()` call sends **no** `X-User-Role`
  (`services/test-management-service/src/utils/question_client.py` — only
  `X-Correlation-Id`). Guard rule: header **present and not TRAINER/ADMIN → 403**;
  header **absent → allow** (internal service-to-service; consistent with the
  platform's trust-the-gateway model documented in CLAUDE.md). Other question
  reads (`GET /questions`, `GET /questions/{id}`) are explicitly deferred to
  W4-F3 with a note.
- Hardening items 6–9 are in-scope for this branch (small, same files), with 9
  implemented as **documentation only** (option already sanctioned by the spec).

## Context

The Week-3 vertical slice merged with one real defect and cross-feature
follow-ups (spec items, severity-ordered):

1. **HIGH** `useServerTimer` re-anchors `mountWall = Date.now()` on every
   `enabled` toggle (`frontend/src/lib/exam/useServerTimer.ts:50-71`) while
   `baseline` stays the original full duration — each submit (active →
   submitting → active) resets the countdown to full. Client auto-submit at
   expiry effectively never fires.
2. **MED** After transient backoff exhaustion, `SUBMIT_FAILED` → `error` is
   terminal (`frontend/src/lib/exam/examReducer.ts:57-64`); no reducer exit, no
   retry affordance in `TestRunner`. A ~3.5s network blip bricks the attempt.
3. **MED** `POST /sessions` mints unlimited ACTIVE sessions per (user, test)
   (`services/test-management-service/src/services/session_service.py:74-123`);
   every `/take/[testId]` refresh re-samples questions and orphans the prior row.
4. **MED/security** `GET /questions/sample` returns full documents incl.
   `correct_answers`/`sample_answer` to any authenticated role via gateway
   pattern `^/v1/api/questions(/.*)?$`.
5. **MED** No `error.tsx`/`not-found.tsx` under `frontend/src/app/take/` —
   `mintSessionServer` throws `ServerApiError` (404/422/502) → raw Next 500 page.
6. **LOW** `useAutosave` is a pure trailing debounce (answers more frequent than
   30s never persist) and keeps PATCHing after semantic 409/410.
7. **LOW** Question text not programmatically associated with its option group;
   `aria-disabled` named in W3-F4 spec step 5 but never asserted.
8. **LOW** Mongo `$sample` may emit duplicates; short-fill is silent.
9. **LOW** Idempotency replay doesn't fingerprint the body; question fetch runs
   under the `SELECT FOR UPDATE` lock — document both contracts.

Constraints/gotchas:

- test-management-service schema is Alembic-owned — partial unique index lands
  as revision **0007** on the 0006 chain, with a data-dedupe step first
  (dev DBs may already hold duplicate ACTIVE rows).
- The W3-F5 integration suite (`tests/integration/`, `--integration` gate, real
  Postgres `eval_ai_itest` + Mongo) is the home for the concurrent double-POST
  test; CI already boots compose Postgres+Mongo+QMS for it.
- Frontend tests: vitest via `pnpm test` (116 passing baseline), `pnpm lint`,
  `pnpm build`.
- QMS tests run on mongomock-motor (`beanie_db` fixture) — route-level guard
  test uses FastAPI `TestClient`/`httpx.ASGITransport` with headers, no Mongo
  dependency for the 403 path.

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` (done — branch fast-forwarded to
  `aa873c1`).
- Feature branch **`richardh-feat-W3F7`** off `richardh` — already exists
  (carried the spec doc, merged via PR #80); continuing on it in worktree
  `w3-remediation`.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, repo style).

## Milestone 1 — Item 1: `useServerTimer` anchors once (HIGH)

Files: `frontend/src/lib/exam/useServerTimer.ts`,
`frontend/src/lib/exam/useServerTimer.test.ts`.

- Replace the per-effect `mountWall` with an absolute client-clock **deadline
  captured once**: `deadlineRef = useRef<number | null>(null)`; on first
  enabled effect run, `deadlineRef.current = Date.now() + baseline * 1000`.
  Every tick derives `remaining = max(0, floor((deadline − Date.now()) / 1000))`.
  Re-enables reuse the stored deadline — the anchor never moves.
- Keep: 1s interval re-derivation (background-tab safety), single-fire
  `onExpire`, clamp at 0, immediate first tick.
- **New test (the gap that let this slip):** disable → re-enable cycle with fake
  timers — advance 30s, toggle `enabled` off and back on, assert `timeRemaining`
  continues from elapsed (baseline − 30), not the full baseline. Plus: deadline
  unchanged across multiple toggles; expiry still fires once after re-enable.

Commit: `fix(w3-f7): anchor useServerTimer deadline once — no reset on re-enable`

## Milestone 2 — Item 2: transient-submit recovery (`SUBMIT_RETRY`)

Files: `frontend/src/lib/exam/examReducer.ts`, `examReducer.test.ts`,
`frontend/src/components/take/TestRunner.tsx`, `TestRunner.test.tsx`.

- Reducer: add `{ type: 'SUBMIT_RETRY' }` — valid **only** from
  `status === 'error'` with `error.kind === 'transient'`; transitions to
  `submitting` (stays locked, clears error). Any other state: no-op. Semantic
  errors keep the terminal lock (no path out).
- `TestRunner`: extract the submit body into a callable that skips the
  `exam.isLocked` guard when invoked as a retry; error banner gains a
  **"Retry submission"** button rendered only for `kind === 'transient'`,
  dispatching `SUBMIT_RETRY` + re-running the submit.
- Tests: reducer — `error(transient) + SUBMIT_RETRY → submitting`,
  `error(semantic) + SUBMIT_RETRY → unchanged`; TestRunner — transient failure
  shows retry button, click retries and confirms on success; semantic failure
  shows no retry button.

Commit: `feat(w3-f7): SUBMIT_RETRY path out of transient submit failure`

## Milestone 3 — Item 3: active-session reuse + race backstop

Files: `services/test-management-service/src/services/session_service.py`,
`src/repositories/session_repository.py`, `src/schemas/session_schema.py`,
`alembic/versions/0007_unique_active_session_per_user_test.py`,
`tests/test_session_service.py`, `tests/integration/test_session_creation_it.py`,
`frontend/src/lib/api/types.ts`, `frontend/src/components/take/TestRunner.tsx`
(+ its test).

Server:

- `SessionRepository.get_active_for_user_test(db, user_id, test_id)` — `SELECT
  ... WHERE user_id=:u AND test_id=:t AND status='ACTIVE'` (newest first).
- `create_session`: before sampling, look up an existing ACTIVE session.
  - Found and **expired** → flip to EXPIRED (same side-effect convention as
    `submit_answer`), continue to mint fresh.
  - Found and live → **reuse**: return `SessionOut` rebuilt from the row —
    fresh `server_now = utcnow()` with the **original `expires_at`** (so the
    client timer shows true remaining time), `current_index`/`total_questions`
    intact, `question` = sanitized fetch of `question_ids[current_index]`, and
    the stored `draft_answers`.
- `SessionOut` gains `draft_answers: dict[str, list[int]] | None = None`
  (present on reuse; `None` on fresh mint — response shape stays
  backward-compatible).
- Alembic **0007**: data-dedupe first (keep newest ACTIVE per (user_id,
  test_id), flip older duplicates to EXPIRED), then partial unique index
  `uq_sessions_active_user_test ON sessions (user_id, test_id) WHERE status =
  'ACTIVE'`.
- Race backstop: wrap the insert; on `IntegrityError` for that index,
  `rollback()` then fetch and return the **winner's row** via the same reuse
  path (no 500 — explicitly unlike the cohort's #73).

Client (refresh-recovery actually lands):

- `TestRunner`: seed the `answers` Map from `session.draft_answers` when
  present; question counter displays `session.current_index + currentIndex + 1`
  so a resumed session doesn't claim "Question 1".

Tests:

- Unit (`test_session_service.py`, mocked repos): reuse returns existing row
  without re-sampling; expired-ACTIVE is flipped and a fresh session minted;
  IntegrityError path returns winner.
- Integration (`test_session_creation_it.py`): second `POST /sessions` for the
  same (user, test) returns the **same `session_id`**; concurrent double-POST
  (two tasks, same pattern as the W3-F5 concurrency test) → both 2xx, same
  `session_id`, exactly **one** ACTIVE row in Postgres.

Commit: `feat(w3-f7): reuse ACTIVE session per (user,test) + partial unique index backstop`

## Milestone 4 — Item 4: role-gate `GET /questions/sample` (security)

Files: `services/question-management-service/src/v1/routes/question_routes.py`,
`services/question-management-service/tests/test_sample_role_guard.py` (new).

- Guard dependency on `/sample` (per the locked decision): read `X-User-Role`;
  **present and not in {TRAINER, ADMIN} → 403**; absent → allow (internal
  TMS call — gateway always injects the real role for browser traffic, so the
  header can't be spoofed-absent through the gateway).
- Docstring note on `/questions` + `/questions/{id}`: same leak class,
  full API-layer RBAC deferred to **W4-F3** (also noted in the feature doc).
- Tests (ASGI transport, no Mongo needed for the 403): `X-User-Role:
  PARTICIPANT` → 403; `TRAINER` → 200; `ADMIN` → 200; no header → 200
  (service-to-service). 200-paths run against the `beanie_db` fixture.

Commit: `fix(w3-f7): role-gate /questions/sample — participants can no longer pull the answer key`

## Milestone 5 — Item 5: take-page error boundary

Files: `frontend/src/app/take/[testId]/error.tsx` (new),
`not-found.tsx` (new), `page.tsx`.

- `page.tsx`: catch `ServerApiError` from `mintSessionServer`; `status === 404`
  → `notFound()`. Other statuses rethrow to the boundary.
- `not-found.tsx`: "Test not found" + link back to the dashboard.
- `error.tsx` (client component): "We couldn't start your test — try again or
  contact your trainer", with the `reset()` retry button. Covers 422 (empty
  bank) and 502 (question service down).

Commit: `feat(w3-f7): error boundary + not-found for /take/[testId]`

## Milestone 6 — Items 6+7: autosave max-wait/halt + a11y

Files: `frontend/src/lib/exam/useAutosave.ts`, `useAutosave.test.ts`,
`frontend/src/components/take/SingleSelectQuestion.tsx`,
`MultiSelectQuestion.tsx`, `TestRunner.test.tsx` (or component tests).

- **Item 6:** schedule delay = `min(intervalMs, time-until-(lastFire +
  intervalMs))` — trailing debounce capped so a continuously-editing candidate
  still persists every `intervalMs` while dirty. On save failure, classify via
  `ApiError.status`: **409/410 → set a halted flag** (status `error`, no
  further PATCHes — session is terminal); other failures keep today's
  retry-on-next-change. Tests: continuous edits every 5s still fire a save at
  ~30s; a 409 stops all subsequent saves.
- **Item 7:** `SingleSelectQuestion` — `aria-labelledby` ties the `RadioGroup`
  to the question text id; `MultiSelectQuestion` — `fieldset` + `legend`
  (sr-only, same text). Pass the question-text element id down from
  `TestRunner`'s `CardTitle`. Tests: assert the association and assert
  `aria-disabled` on locked inputs (the W3-F4 step-5 gap).

Commit: `feat(w3-f7): autosave max-wait + semantic halt; a11y question/option association`

## Milestone 7 — Items 8+9: `$sample` dedupe + contract docs

Files: `services/test-management-service/src/services/session_service.py`,
`tests/test_session_service.py`, `frontend/src/lib/api/sessions.ts`,
`src/utils/question_client.py` (comment only).

- **Item 8:** dedupe `question_ids` (order-preserving) before persisting;
  accept the shorter set. `logger.warning` when the final count <
  `test.number_of_questions` (short-fill no longer silent). Unit test: dupes
  collapse; warning emitted on short-fill.
- **Item 9 (docs only):** JSDoc on the key-minting site in
  `frontend/src/lib/api/sessions.ts` — an `Idempotency-Key` is bound to one
  payload; reusing a key with a different body replays the stored response
  (no fingerprint check server-side). Comment at the
  `question_client.get_question` call inside `submit_answer` — runs under the
  row lock; blast radius = this session only; timeout budget = 10s × ≤3
  attempts per fetch (`_TIMEOUT`/`_MAX_RETRIES`).

Commit: `fix(w3-f7): dedupe sampled question ids + document idempotency/lock contracts`

## Testing & validation

Pass bar — all green, no regressions:

1. **Frontend** (`cd frontend`): `pnpm test` (baseline 116 + new specs),
   `pnpm lint`, `pnpm build`.
2. **test-management-service** (`cd services/test-management-service`):
   `pytest --cov` (unit; baseline 94 passed/4 skipped + new),
   then integration vs real containers:
   `docker compose up -d --wait postgres mongo question-management-service` →
   `pytest --integration tests/integration/` (baseline 4 + new reuse/double-POST).
3. **question-management-service** (`cd services/question-management-service`):
   `pytest --cov` (+ new role-guard tests).
4. **Compose smoke:** `docker compose up --build -d` →
   - `curl /v1/api/questions/sample` through the gateway as PARTICIPANT → 403;
     as TRAINER → 200 (item 4 live);
   - `POST /sessions` twice as the same participant → same `session_id`,
     one ACTIVE row (item 3 live);
   - Alembic 0007 applies cleanly on the dev DB (TMS `start.sh` runs it).
5. **Timer acceptance** ("countdown never increases across ≥2 submits") —
   covered automatically by the new disable→re-enable spec; flag the manual
   live-session check in the final report for the user to eyeball.

## Requirements review (final milestone)

- Re-read `docs/features/w3-f7-review-remediation.md` items 1–9 + Acceptance;
  verify each against the actual diff (file:line + commit evidence).
- Update the feature doc: check off items, add evidence.
- `docs/FEATURE_STATUS.md`: **W3-F7 → ✅**, **W3-F4 → back to ✅** (gated on
  item 1), refresh "Last assessed".
- Also tick the re-opened note in `w3-f4-autosave-exam-client.md`.

Commit: `docs(w3-f7): mark remediation complete + requirements review evidence`

## Push gate

Push `richardh-feat-W3F7` to origin **only if** every suite above is green
**and** the requirements review confirms items 1–5 (+6–9 as delivered) are met.
Otherwise stop, leave the branch local, report what's outstanding.
