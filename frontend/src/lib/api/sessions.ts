/**
 * Quiz session browser client (W3-F3 + W3-F4).
 *
 * Sequential-reveal contract: submit the current question's answer and receive
 * the next sanitized question. Routed through the BFF proxy (/api/v1/...),
 * which lifts the auth cookie to a Bearer header for the gateway — the raw
 * cookie never leaves the server. Both calls are wrapped in `fetchWithRetry`
 * (W3-F4): a flaky network retries with backoff while a server rejection
 * (409/410/422) halts immediately.
 */
import { api } from './client';
import { fetchWithRetry } from '@/lib/exam/errors';
import { AnswerResult, DraftSaveResult } from './types';

/**
 * Mint a stable idempotency key for one logical submission. Reuse it across
 * that submission's retries so a network blip cannot double-score; mint a fresh
 * one per new submission (the server binds a key to the FIRST body it sees, so
 * a key reused with a different payload silently replays the stored response).
 */
export function newIdempotencyKey(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
}

/**
 * Submit the answer to the session's current question and advance.
 *
 * `submittedAnswers` is the candidate's selection for the current question:
 * 1-indexed option_ids for MCQ/MULTI, or a single bool for TRUE_FALSE.
 * `questionId`, when supplied, lets the server reject an out-of-order/stale
 * submission. `idempotencyKey` is generated once per logical submit and reused
 * across retries (W3-F4) so a transient retry replays rather than re-scores.
 */
export function submitAnswer(
  sessionId: string,
  submittedAnswers: (number | boolean)[],
  questionId?: string,
  idempotencyKey: string = newIdempotencyKey(),
): Promise<AnswerResult> {
  return fetchWithRetry(() =>
    api.post<AnswerResult>(
      `/v1/api/sessions/${sessionId}/answer`,
      { submitted_answers: submittedAnswers, question_id: questionId },
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
