/**
 * Browser-side quiz session calls (W3-F4), routed through the BFF proxy.
 *
 * Both are wrapped in fetchWithRetry so a transient failure (network / 5xx)
 * backs off and retries while a semantic failure (409/410/422) surfaces at
 * once. The retried answer submit reuses the SAME Idempotency-Key, so the
 * backend replays the original result instead of double-scoring.
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

/** Autosave the in-progress answer map (advisory, last-write-wins). */
export function saveDraft(
  sessionId: string,
  answers: Record<string, number[]>
): Promise<DraftSaveResult> {
  return fetchWithRetry(() =>
    api.patch<DraftSaveResult>(`/v1/api/sessions/${sessionId}/draft`, { answers })
  );
}
