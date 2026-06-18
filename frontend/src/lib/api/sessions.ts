import type { QuizQuestion } from './types';

export type { QuizQuestion };

export interface SessionRead {
  session_id: string;
  session_token: string;
  test_id: number;
  user_id: number;
  status: string;
  current_index: number;
  server_now: string;
  expires_at: string;
  first_question: QuizQuestion | null;
}

export interface AnswerResponse {
  session_id: string;
  question_id: string;
  question_index: number;
  score: number | null;
  algorithm: string;
  session_status: string;
  current_index: number;
  next_question: QuizQuestion | null;
}

/** Submit one answer and receive the next question (client-side via BFF proxy). */
export async function submitAnswer(
  sessionId: string,
  questionId: string,
  submittedAnswers: (number | boolean | string)[],
): Promise<AnswerResponse> {
  const res = await fetch(`/api/v1/sessions/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: questionId,
      submitted_answers: submittedAnswers,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => String(res.status));
    throw new Error(`Answer submission failed (${res.status}): ${detail}`);
  }
  return res.json() as Promise<AnswerResponse>;
}
