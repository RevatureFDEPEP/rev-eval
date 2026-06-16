/**
 * Browser-side quiz session calls (W3-F4), routed through the BFF proxy.
 *
 * The answer submit is wrapped in fetchWithRetry so a transient failure
 * (network / 5xx) backs off and retries while a semantic failure (409/410/422)
 * surfaces at once. The retried submit reuses the SAME Idempotency-Key, so the
 * backend replays the original result instead of double-scoring.
 *
 * The draft save is deliberately NOT retried. A retry backs off for up to ~2s,
 * during which a newer debounce can save fresher answers; the retried older
 * snapshot could then land last and win last-write-wins with stale data. Since
 * autosave is advisory and the next debounce re-saves anyway, a single attempt
 * that fails fast (surfacing "error", self-healed on the next change) is both
 * simpler and correct.
 */

import { api } from './client';
import type { AnswerResult, DraftSaveResult } from './types';
import { fetchWithRetry } from '@/lib/exam/errors';

/**
 * Submit the current question's answer. `idempotencyKey` must be stable across
 * retries of the same submission (generate one per question, not per attempt).
 */
export function submitAnswer(
  sessionId: string,
  submittedAnswers: number[],
  questionId: string,
  idempotencyKey: string
): Promise<AnswerResult> {
  return fetchWithRetry(() =>
    api.post<AnswerResult>(
      `/v1/api/sessions/${sessionId}/answer`,
      { question_id: questionId, submitted_answers: submittedAnswers },
      { headers: { 'Idempotency-Key': idempotencyKey } }
    )
  );
}

/**
 * Autosave the in-progress answer map (advisory). Single attempt, no retry —
 * see the module header for why retrying drafts is unsafe. `clientVersion` is a
 * strictly increasing stamp; the server applies the write only when it exceeds
 * the stored version, so a late/reordered stale snapshot can't clobber a fresher
 * one (monotonic guard).
 */
export function saveDraft(
  sessionId: string,
  answers: Record<string, number[]>,
  clientVersion: number
): Promise<DraftSaveResult> {
  return api.patch<DraftSaveResult>(`/v1/api/sessions/${sessionId}/draft`, {
    answers,
    client_version: clientVersion,
  });
}
