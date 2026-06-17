/**
 * Manual grading API (W5-F1)
 *
 * Trainer flow for grading free-text answers that can't be auto-scored. A
 * PENDING_REVIEW answer is listed in the queue and graded with a 0..1 score +
 * optional feedback. Routes to test-management-service via the gateway.
 */

import { api } from './client';

export interface PendingAnswer {
  answer_id: number;
  session_id: string;
  user_id: number;
  question_index: number;
  question_id: string;
  submitted_answers: unknown[];
  submitted_at: string | null;
  test_id: number;
  test_name: string | null;
  question_text: string | null;
  sample_answer: string | null;
}

export interface GradingQueue {
  items: PendingAnswer[];
  total: number;
  page: number;
  size: number;
}

export interface GradedAnswer {
  answer_id: number;
  session_id: string;
  question_index: number;
  score: number;
  is_correct: boolean;
  grading_status: string;
  feedback: string | null;
  graded_by_id: number | null;
  graded_at: string | null;
  session_needs_grading: boolean;
}

/** List free-text answers awaiting a manual grade (trainer-only). */
export async function getGradingQueue(params?: {
  test_id?: number;
  page?: number;
  size?: number;
}): Promise<GradingQueue> {
  const q = new URLSearchParams();
  if (params?.test_id != null) q.set('test_id', String(params.test_id));
  if (params?.page != null) q.set('page', String(params.page));
  if (params?.size != null) q.set('size', String(params.size));
  const qs = q.toString();
  return api.get<GradingQueue>(`/v1/api/sessions/grading-queue${qs ? `?${qs}` : ''}`);
}

/** Grade one free-text answer with a 0..1 score + optional feedback. */
export async function gradeAnswer(
  sessionId: string,
  questionIndex: number,
  body: { score: number; feedback?: string | null },
): Promise<GradedAnswer> {
  return api.post<GradedAnswer>(
    `/v1/api/sessions/${sessionId}/answers/${questionIndex}/grade`,
    body,
  );
}
