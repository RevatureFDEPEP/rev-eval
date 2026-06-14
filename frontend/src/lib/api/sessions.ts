/**
 * Quiz session browser client (W3-F3).
 *
 * Sequential-reveal contract: submit the current question's answer and receive
 * the next sanitized question. Routed through the BFF proxy (/api/v1/...),
 * which lifts the auth cookie to a Bearer header for the gateway — the raw
 * cookie never leaves the server.
 */
import { api } from './client';
import { AnswerResult } from './types';

/**
 * Submit the answer to the session's current question and advance.
 *
 * `submitted_answers` is the candidate's selection for the current question:
 * 1-indexed option_ids for MCQ/MULTI, or a single bool for TRUE_FALSE. The
 * `Idempotency-Key` makes a retried submit replay the prior server response
 * instead of re-scoring; a fresh key is minted per call (skeleton scope —
 * retry-with-stable-key is W3-F4).
 */
export async function submitAnswer(
  sessionId: string,
  submittedAnswers: (number | boolean)[],
  questionId?: string,
): Promise<AnswerResult> {
  const idempotencyKey =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${sessionId}-${Date.now()}-${Math.round(Math.random() * 1e9)}`;

  return api.post<AnswerResult>(
    `/v1/api/sessions/${sessionId}/answer`,
    { submitted_answers: submittedAnswers, question_id: questionId },
    { 'Idempotency-Key': idempotencyKey },
  );
}
