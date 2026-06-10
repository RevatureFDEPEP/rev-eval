# W3-F4 — Auto-Saving Exam Client (Server-Anchored Timer + Submit-Lock UX) — Plan

**Feature:** W3-F4 — Auto-Saving Exam Client
**Detail doc:** [`docs/features/w3-f4-autosave-exam-client.md`](../features/w3-f4-autosave-exam-client.md)
**Spec:** `days_11_15_features.md` §4 (Day 14), Implementation Details 1–4
**Depends on:** W3-F3 (✅ — extends `TestRunner` + the `answers` `Map<string, number[]>`), W3-F2 (✅ — `POST /sessions/{id}/answer` state machine + `SUBMITTED`/`EXPIRED` enforcement; submit-lock is only meaningful once server-side terminal states are enforced), W3-F1 (✅ — `server_now`/`expires_at` timing contract)
**Unblocks:** W3-F6 (Playwright E2E — needs the full quiz UI incl. timer + submit-lock)

## Locked decisions (presented for approval)

- **Submit = the forward answer loop (realizes TestRunner.tsx:15's W3-F4 TODO).**
  The W3-F1/F2 backend is strictly sequential: `POST /sessions/{id}/answer` scores
  the *current* question, advances `current_index`, returns `next_question`, and
  flips `status → SUBMITTED` only on the **last** question. So "submit the exam" is
  the act of posting each answer in order. The primary action button posts the
  current answer (`POST /answer` with an `Idempotency-Key`), appends the returned
  `next_question` to the live `questions[]`, and advances. On the final question
  the `AnswerResult` returns `status: "SUBMITTED"` → lock + confirmation. This is
  exactly the seam F3 left open; no new bulk/submit endpoint is added.
- **Answered questions are read-only on review.** `Prev` still navigates back
  (React state only, per F3) but an already-answered question renders with inputs
  disabled — the backend has already scored it and does not accept re-answers.
  Track answered indices in the exam reducer.
- **Draft autosave is a separate, advisory recovery snapshot.** `PATCH
  /sessions/{id}/draft` persists the full in-progress `answers` map **without**
  advancing `current_index` or changing `status`. It is last-write-wins (no
  idempotency key needed) and exists only so a crash/close mid-question doesn't
  lose unsaved selections. It does **not** score.
- **New `draft_answers` JSON column on `sessions`** (Alembic `0006`, chained off
  `0005`). test-management-service schema is Alembic-owned — `create_all` is not
  used. Column is nullable; default empty.
- **Timer reuses the existing `Timer.tsx` display component** (W3-F3 already shipped
  it: props `timeRemaining`/`formatTime`/`isWarning`/`isCritical`). W3-F4 adds the
  *logic* hook that feeds it; the dumb display is untouched.
- **Gateway:** `^/v1/api/sessions(/.*)?$` (`api-gateway-service/main.py:55`) already
  matches `PATCH /sessions/{id}/draft`. **No ROUTES change.**

## Context — what exists now

- **Backend (test-management-service):**
  - `Session` model (`src/models/session.py`): `session_id` (UUID PK), `test_id`,
    `user_id`, `session_token`, `server_now`, `expires_at`, `status`
    (`ACTIVE`/`SUBMITTED`/`EXPIRED`), `current_index`, `submitted_at`, `question_ids`
    (JSON ordered list). **No draft column yet.**
  - `session_service.py`: `create_session()` + `submit_answer()` (pessimistic
    `SELECT FOR UPDATE`, idempotency replay, state gate → `SessionTerminalError`/
    `SessionExpiredError` = 409, scoring, advance, finalize on last). Exception
    classes already defined.
  - `session_route.py`: `POST /sessions/` (201) + `POST /sessions/{id}/answer`
    (requires `Idempotency-Key` header; 404/403/409/422/502 mapping).
  - `session_repository.py`: `get_by_id`, `get_for_update`, `create`, `flush`.
  - `session_schema.py`: `SessionCreate`, `AnswerSubmit { submitted_answers }`,
    `SanitizedQuestion`, `SessionOut`, `AnswerResult { session_id, question_id,
    current_index, total_questions, status, submitted_at, next_question }`.
  - Alembic head = **`0005`** (`0004` sessions table, `0005` answers/idempotency).
- **Frontend:**
  - `components/take/TestRunner.tsx` (`'use client'`): owns `currentIndex` +
    `answers` `Map<string, number[]>`, seeds `questions[]` from `session.question`,
    polymorphic `renderQuestion`, clamped Prev/Next. **No timer/autosave/submit.**
  - `components/quiz/Timer.tsx`: display-only countdown badge (color states).
  - `components/take/{SingleSelectQuestion,MultiSelectQuestion}.tsx`: leaf inputs
    (`{ question, selected, onChange }`).
  - `app/take/[testId]/page.tsx`: server-mints the session, wraps
    `<AuthProvider><TestRunner session={…} /></AuthProvider>`.
  - `lib/api/server.ts`: `mintSessionServer` / `getIdentityServer` (server-only).
  - `lib/api/client.ts`: browser BFF client — `api.get/post/put/delete`. **No
    `patch`, no session-specific fns.**
  - `app/api/v1/[...path]/route.ts`: generic BFF proxy, forwards **all** verbs incl.
    PATCH + arbitrary headers (`Idempotency-Key` passes through) with Bearer JWT.
  - `lib/api/types.ts`: `SessionOut`, `SanitizedQuestion`, `AuthIdentity`. **No
    `AnswerResult`/`AnswerSubmit`/draft types.**
  - Vitest configured (`vitest.config.ts` jsdom + `vitest.setup.ts`); existing specs
    under `components/take/` + `components/quiz/`.

## Constraints / gotchas

- Timer must derive from **`server_now`/`expires_at`**, never the client clock:
  `remaining₀ = (expires_at − server_now)`; live `remaining = remaining₀ −
  (Date.now()/1000 − mountWallClock)`. Absorbs client skew (spec step 1).
- `Idempotency-Key` is **required** on `POST /answer` (422 if blank) — generate one
  per question submission (stable across retries of the *same* submission).
- Error classification: **transient** = network failure / 502 / 503 / 504 →
  exponential-backoff retry; **semantic** = 409 / 410 / 422 → surface + halt, **no
  retry** (spec step 3). A 409 from a terminal/expired session must not retry-storm.
- Submit-lock is **optimistic for inputs/timer** (`isLocked` set before the server
  responds) but the *result/confirmation* is a **confirmed** update — only render
  "submitted" after the server acks `SUBMITTED`; on failure surface the error and
  keep the inputs locked rather than showing a rejected result (spec step 4 /
  detail doc step 4).
- Schema change goes through `alembic revision` (chained off `0005`), not
  `create_all`.

---

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W3F4`** off `richardh` before any code change; confirm
  with `git branch --show-current`.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — Backend: `draft_answers` column + Alembic 0006 + schemas
- `src/models/session.py` — add `draft_answers = Column(JSON, nullable=True)`
  (in-progress selections, not scored).
- `alembic/versions/0006_add_session_draft_answers.py` — `down_revision = '0005'`;
  `op.add_column('sessions', sa.Column('draft_answers', sa.JSON(), nullable=True))`
  + matching `downgrade`.
- `src/schemas/session_schema.py` — `DraftSave { answers: Dict[str, List[int]] }`
  (request) and `DraftSaveResult { session_id, status, current_index, saved_at }`
  (response; echoes that index/status did **not** advance).
- Commit: `feat(w3-f4): sessions.draft_answers column + Alembic 0006 + draft schemas`.

### M2 — Backend: `save_draft` service + `PATCH /sessions/{id}/draft` route
- `src/services/session_service.py` — `save_draft(db, session_id, user_id, answers)`:
  `get_by_id` → 404 if missing; 403 if `user_id` mismatch; **409** if `status !=
  ACTIVE` or `expires_at` passed (semantic — client halts, no retry). Otherwise set
  `draft_answers`, `flush`, `commit`; return `DraftSaveResult` with the **unchanged**
  `current_index`/`status` and `saved_at = utcnow()`. Reuse existing
  `SessionNotFoundError`/`SessionForbiddenError`/`SessionTerminalError`/
  `SessionExpiredError`.
- `src/v1/routes/session_route.py` — `@router.patch("/{session_id}/draft",
  response_model=DraftSaveResult)`; map 404/403/409 like `submit_answer`.
- `services/test-management-service/tests/` — pytest for `save_draft`: happy path
  persists + does not advance; 403 on wrong user; 409 on SUBMITTED/EXPIRED session
  (asserts no retry-worthy 5xx). (Matches the W3-F1/F2 service-test convention.)
- Commit: `feat(w3-f4): PATCH /sessions/{id}/draft autosave endpoint + tests`.

### M3 — Frontend: API types + PATCH client + session calls + error classifier
- `lib/api/types.ts` — add `AnswerSubmit`, `AnswerResult`, `DraftSave`,
  `DraftSaveResult` mirroring the backend; an `ExamErrorKind = 'transient' |
  'semantic'`.
- `lib/api/client.ts` — add `api.patch<T>(endpoint, data, init?)` and allow extra
  headers (for `Idempotency-Key`) on `post`.
- `lib/exam/errors.ts` (new) — `classifyError(status?: number)` → transient (network/
  502/503/504) vs semantic (409/410/422); `fetchWithRetry(fn, { maxRetries, baseMs })`
  = exponential backoff on transient only, immediate throw on semantic.
- `lib/api/sessions.ts` (new) — `submitAnswer(sessionId, submittedAnswers, key)`
  (`POST /sessions/{id}/answer`, retry-wrapped) and `saveDraft(sessionId, answers)`
  (`PATCH /sessions/{id}/draft`, retry-wrapped), surfacing a typed error.
- Commit: `feat(w3-f4): session API client (answer/draft) + transient-vs-semantic error classifier`.

### M4 — Frontend: timer + autosave hooks + exam reducer
- `lib/exam/useServerTimer.ts` (new) — `useServerTimer(serverNow, expiresAt,
  onExpire)`: compute mount-anchored remaining seconds (skew-absorbing formula),
  `setInterval` 1s decrement + clamp at 0; call `onExpire` exactly once at zero;
  derive `isWarning` (<300s) / `isCritical` (<60s) + `formatTime`. Stops when locked.
- `lib/exam/useAutosave.ts` (new) — `useAutosave(sessionId, answers, enabled)`:
  debounced 30s `saveDraft`; cancels on unmount; disabled once locked. Returns
  `saveStatus`.
- `lib/exam/examReducer.ts` (new) — `useReducer` state:
  `{ status: 'active'|'submitting'|'submitted'|'error', isLocked, answeredIndices:
  Set<number>, saveStatus, error }`. Actions: `SUBMIT_START` (→ submitting, isLocked
  true), `SUBMIT_CONFIRMED(result)` (SUBMITTED → submitted/stay-locked; else →
  active/unlock + mark answered + advance), `SUBMIT_FAILED(error)` (semantic →
  error + halt, keep locked), `SAVE_*`.
- Commit: `feat(w3-f4): server-anchored timer + debounced autosave hooks + exam reducer`.

### M5 — Frontend: wire TestRunner (timer, autosave, submit-and-lock, next_question)
- `components/take/TestRunner.tsx` —
  - render `<Timer>` fed by `useServerTimer`; `onExpire` auto-invokes submit of the
    current question.
  - `useAutosave` PATCHes the answers map every 30s while `active`.
  - replace `Next` with a primary submit handler: dispatch `SUBMIT_START` (optimistic
    lock + timer stop), `submitAnswer(...)`, on ack append `next_question` to
    `questions[]` + `SUBMIT_CONFIRMED`; on semantic failure `SUBMIT_FAILED` (surface,
    halt). Final question → confirmation state.
  - inputs (`Single/MultiSelectQuestion`) + buttons get `disabled`/`aria-disabled`
    when `isLocked` or when reviewing an already-answered index (`Prev`).
  - render a confirmation panel when `status === 'submitted'` and an error banner
    when `status === 'error'`.
- Commit: `feat(w3-f4): TestRunner timer + autosave + submit-and-lock via useReducer`.

### M6 — Vitest tests
- `lib/exam/useServerTimer.test.ts` — fake timers: decrement, skew absorption, single
  `onExpire` at zero.
- `lib/exam/useAutosave.test.ts` — debounced PATCH fires after 30s; not before; not
  when locked.
- `lib/exam/examReducer.test.ts` — transitions incl. optimistic lock + confirmed
  unlock/submitted + semantic halt.
- `lib/exam/errors.test.ts` — `classifyError` mapping; `fetchWithRetry` backs off on
  502 but throws immediately on 422 (no retry storm).
- `components/take/TestRunner.test.tsx` — extend: locked-state asserts
  `disabled`/`aria-disabled` on interactive elements; mocked `submitAnswer` drives
  the submit→confirmation flow.
- Commit: `test(w3-f4): timer/autosave/reducer/error-classifier + TestRunner locked-state`.

### M7 — Requirements review + status docs
- Re-read the 5 detail-doc Steps + spec §4 Implementation Details 1–4; verify each
  against the diff, citing `file:line`/commit.
- Update `docs/features/w3-f4-autosave-exam-client.md` (check off steps, add evidence,
  clear "Remaining") + the `FEATURE_STATUS.md` W3-F4 row → ✅.
- Commit: `docs(w3-f4): mark feature complete + requirements review evidence`.

## Testing & validation

- **Backend** (`cd services/test-management-service`):
  - `alembic upgrade head` applies `0006` cleanly (and `downgrade -1` reverts).
  - `pytest --cov` — green, incl. the new `save_draft` tests.
- **Frontend** (`cd frontend`):
  - `pnpm test` (`vitest run`) — all green incl. the M6 specs.
  - `pnpm lint` — clean.
  - `pnpm build` — succeeds (no `server-only` leak; client/server boundaries valid).
- **Smoke (optional, if Docker available):** `docker compose up --build`, log in as a
  seeded participant, open `/take/<testId>`: timer counts down from server timing;
  the network tab shows a `PATCH …/draft` ~every 30s; submitting disables inputs +
  stops the timer immediately and renders the confirmation after the ack; letting the
  timer hit zero auto-submits; killing the network mid-save retries (transient) while
  a forced 409 surfaces and halts.

**Pass bar:** backend `pytest --cov` + `alembic upgrade head`, and frontend
`pnpm test` + `pnpm lint` + `pnpm build`, all succeed; every detail-doc Step is
evidenced in the requirements review.

## Push gate

Push `richardh-feat-W3F4` to origin **only if** all tests pass **and** the
requirements review confirms all 5 Steps. Otherwise stop, keep the branch local, and
report exactly what's outstanding.
