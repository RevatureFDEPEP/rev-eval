/**
 * Browser-side quiz-session calls (W3-F4). These run from the interactive exam
 * client, so they go through the BFF proxy (`/api/v1/...`) which lifts the JWT
 * from the auth cookie. Both are wrapped in `fetchWithRetry` so a flaky network
 * retries with backoff while a server rejection (409/410/422) halts immediately.
 */
import { api } from './client';
import { fetchWithRetry } from '@/lib/exam/errors';
import type { AnswerResult, DraftSaveResult } from './types';

/**
 * A stable per-submission idempotency key (reused across this submit's retries).
 *
 * CONTRACT (W3-F7 item 9a): a key is bound to ONE payload. The server does not
 * fingerprint the request body — replaying a key with a *different* body
 * silently returns the response stored for the first request. Always mint a
 * fresh key per logical submission (as the default parameter does) and reuse
 * it only for byte-identical retries of that same submission.
 */
function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

/**
 * Submit the candidate's answer to the current question (W3-F2 `POST
 * /sessions/{id}/answer`). The `Idempotency-Key` is generated once and reused
 * across retries so a network blip cannot double-score. Returns the advance
 * state incl. `next_question` (or `status: "SUBMITTED"` on the final question).
 */
export function submitAnswer(
  sessionId: string,
  submittedAnswers: number[],
  idempotencyKey: string = newIdempotencyKey(),
): Promise<AnswerResult> {
  return fetchWithRetry(() =>
    api.post<AnswerResult>(
      `/v1/api/sessions/${sessionId}/answer`,
      { submitted_answers: submittedAnswers },
      { 'Idempotency-Key': idempotencyKey },
    ),
  );
}

/**
 * Autosave the full in-progress answer map (W3-F4 `PATCH /sessions/{id}/draft`).
 * Advisory + last-write-wins: it does not score or advance the session.
 */
export function saveDraft(
  sessionId: string,
  answers: Record<string, number[]>,
): Promise<DraftSaveResult> {
  return fetchWithRetry(() =>
    api.patch<DraftSaveResult>(`/v1/api/sessions/${sessionId}/draft`, { answers }),
  );
}
