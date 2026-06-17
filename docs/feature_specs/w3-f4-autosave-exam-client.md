# W3-F4 — Auto-Saving Exam Client with Server-Anchored Timer and Submit-Lock UX

*Layer a live countdown timer derived from server timing, periodic autosave, graceful network failure handling, and an immediate submit-and-lock interaction on top of the Day 13 skeleton.*

* **Curriculum Fit**: Day 14 (Client-side temporal state and timers, submit-and-lock UX patterns, graceful network failure handling, optimistic updates vs. server confirmation, React state management with useReducer, component unit testing with Vitest).
* **Prerequisites**: Day 14 topics.
* **Cross-Week Dependencies**: Requires W3-F3 (Test-Taking Frontend Skeleton) — the TestRunner component and answer Map state must exist as the base layer this feature extends. Requires W3-F2 (Scoring Engine) — the `PATCH /sessions/{id}/draft` endpoint relies on the session state machine and status fields introduced in W3-F2; the submit-lock UX is only meaningful once the server-side submitted state is enforced.
* **Required for**: W3-F6 (Playwright E2E and Smoke Script — the full quiz-taking UI including timer and submit-lock must be in place for the happy-path flow to complete)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours

## Implementation Details

1. On TestRunner mount, compute the remaining seconds as `(expires_at - server_now) - (Date.now() / 1000 - mount_time)` to absorb client clock skew. Run a `setInterval` decrement and render the remaining time. When the counter reaches zero, call the submit handler automatically.
2. Add a `PATCH /sessions/{id}/draft` endpoint to test-management-service that accepts a partial answers payload and persists it without advancing `current_index` or changing session status. Wire a debounced autosave call from TestRunner on a 30-second interval.
3. Classify fetch errors into transient (network timeouts, 502/503/504 — retry with exponential backoff) and semantic (409 Conflict, 410 Gone, 422 Validation — surface immediately and halt) so retries are only issued where they can succeed.
4. On submit, immediately set an `isLocked: true` flag in component state (using `useReducer` for the full session state machine) before the server responds, disabling all inputs and the timer. Autosave is a confirmed update (wait for server ack before clearing draft); submission is also confirmed (do not unlock until the server confirms, to avoid prematurely showing a result that was rejected).
5. Write Vitest component unit tests for the timer decrement logic, the autosave debounce trigger, and the locked state rendering, asserting DOM attributes (`disabled`, `aria-disabled`) on interactive elements when `isLocked` is true.
