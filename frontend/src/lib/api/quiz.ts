/**
 * Quiz session API — server-authoritative quiz-taking slice.
 *
 * Talks to the test-management-service `/v1/api/sessions` contract through the
 * BFF + gateway. Timing is owned by the server (`server_now`/`expires_at`);
 * answer submissions are idempotent via an `Idempotency-Key` header.
 *
 * Participant responses never contain answer keys or per-question correctness —
 * only the final `/submit` returns an aggregate score.
 */
import { api, ApiError } from './client';

export type SelectedAnswer = number | boolean;

export interface QuizQuestionOut {
  question_id: string;
  question_index: number;
  question_type: string;
  question_text: string;
  options?: Array<Record<string, unknown>> | null;
}

export interface QuizSessionStart {
  session_id: string;
  session_token: string;
  server_now: string;
  expires_at: string;
  status: string;
  current_index: number;
  total_questions: number;
  question: QuizQuestionOut;
}

export interface QuizSessionState {
  session_id: string;
  status: string;
  server_now: string;
  expires_at: string;
  current_index: number;
  total_questions: number;
  draft_answers: Record<string, SelectedAnswer[]>;
  questions: QuizQuestionOut[];
  total_score?: number | null;
  max_score?: number | null;
  percentage_score?: number | null;
}

export interface DraftResponse {
  session_id: string;
  status: string;
  server_now: string;
  expires_at: string;
  current_index: number;
  draft_answers: Record<string, SelectedAnswer[]>;
}

export interface AnswerResult {
  session_id: string;
  question_id: string;
  recorded: boolean;
  answered_count: number;
  total_questions: number;
  server_now: string;
  expires_at: string;
}

export interface QuizSubmitResult {
  session_id: string;
  status: string;
  submitted_at: string;
  total_score: number;
  max_score: number;
  percentage_score: number;
  correct_count: number;
  answered_count: number;
  total_questions: number;
}

/** Create a durable, server-timed quiz session. */
export async function createQuizSession(input: {
  test_id: number;
  submission_id?: number | null;
}): Promise<QuizSessionStart> {
  return api.post<QuizSessionStart>('/v1/api/sessions', input);
}

/** Fetch full session state (resume/refresh) — safe questions, draft, timing. */
export async function getQuizSession(sessionId: string): Promise<QuizSessionState> {
  return api.get<QuizSessionState>(`/v1/api/sessions/${sessionId}`);
}

/** Autosave buffered answers and/or the current cursor to the durable session. */
export async function saveQuizDraft(
  sessionId: string,
  patch: { current_index?: number; answers?: Record<string, SelectedAnswer[]> },
): Promise<DraftResponse> {
  return api.patch<DraftResponse>(`/v1/api/sessions/${sessionId}/draft`, patch);
}

/**
 * Submit and score one answer. Pass a stable `idempotencyKey` so a network
 * retry replays the recorded result instead of double-recording.
 */
export async function submitQuizAnswer(
  sessionId: string,
  answer: { question_id: string; selected_answers: SelectedAnswer[] },
  idempotencyKey?: string,
): Promise<AnswerResult> {
  const headers = idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined;
  return api.post<AnswerResult>(
    `/v1/api/sessions/${sessionId}/answers`,
    answer,
    headers,
  );
}

/** Finalize the session and return the aggregate score. Idempotent. */
export async function submitQuizSession(sessionId: string): Promise<QuizSubmitResult> {
  return api.post<QuizSubmitResult>(`/v1/api/sessions/${sessionId}/submit`, {});
}

/** Narrow an unknown error to the API status code for retry/lock handling. */
export function quizErrorStatus(err: unknown): number | null {
  return err instanceof ApiError ? err.status : null;
}
