/**
 * Quiz Sessions API
 *
 * Functions for managing quiz test sessions with the AI Quiz Service.
 * Handles two-part adaptive quizzes (Part A + Part B).
 */

import { api } from './client';
import {
  TestSessionCreate,
  TestSession,
  PartAQuestionsResponse,
  PartBQuestionsResponse,
  PartAAnswersSubmit,
  PartBAnswersSubmit,
  QuizSubmitResponse,
} from './types';

/**
 * Create a new test session when user starts a quiz
 *
 * @param data - Session creation data (test_id, submission_id, user_id, etc.)
 * @returns Created test session with session_id
 */
export async function createTestSession(data: TestSessionCreate): Promise<TestSession> {
  // Backend returns TestSessionOut with 'id' field, we need to map to 'session_id'
  const response = await api.post<TestSession>('/v1/api/test-sessions/', data);
  return {
    ...response,
    session_id: response.id || response.session_id,
    current_part: null,
  };
}

/**
 * Get Part A questions (11 questions: 3 easy, 4 medium, 4 hard)
 *
 * @param sessionId - MongoDB session ID
 * @returns Part A questions (without correct answers)
 * @note Backend fetches test_id from session automatically
 */
export async function getPartAQuestions(
  sessionId: string
): Promise<PartAQuestionsResponse> {
  return api.get<PartAQuestionsResponse>(
    `/v1/api/test-sessions/${sessionId}/part-a/questions`
  );
}

/**
 * Submit Part A answers for grading
 *
 * @param data - Session ID and array of answers
 * @returns Part A score and analysis
 */
export async function submitPartA(data: PartAAnswersSubmit): Promise<QuizSubmitResponse> {
  const { session_id, answers } = data;
  return api.post<QuizSubmitResponse>(
    `/v1/api/test-sessions/${session_id}/part-a/submit`,
    { session_id, answers }  // Backend expects both session_id and answers in body
  );
}

/**
 * Get Part B questions (adaptive based on Part A performance)
 *
 * @param sessionId - MongoDB session ID
 * @returns Part B questions (adaptive difficulty, excludes Part A questions)
 * @note Backend fetches test_id from session and adapts based on Part A performance
 */
export async function getPartBQuestions(
  sessionId: string
): Promise<PartBQuestionsResponse> {
  return api.get<PartBQuestionsResponse>(
    `/v1/api/test-sessions/${sessionId}/part-b/questions`
  );
}

/**
 * Submit Part B answers and complete the test
 *
 * @param data - Session ID and array of answers
 * @returns Final quiz results (score, analysis)
 */
export async function submitPartB(data: PartBAnswersSubmit): Promise<QuizSubmitResponse> {
  const { session_id, answers } = data;
  return api.post<QuizSubmitResponse>(
    `/v1/api/test-sessions/${session_id}/part-b/submit`,
    { session_id, answers }  // Backend expects both session_id and answers in body
  );
}

/**
 * Get test session details
 *
 * @param sessionId - MongoDB session ID
 * @returns Complete session information
 */
export async function getTestSession(sessionId: string): Promise<TestSession> {
  const response = await api.get<TestSession>(`/v1/api/test-sessions/${sessionId}`);
  return {
    ...response,
    session_id: response.id || response.session_id,
  };
}

/**
 * Get test session by submission ID
 *
 * @param submissionId - SQL submission ID
 * @returns Test session associated with the submission
 */
export async function getTestSessionBySubmission(submissionId: number): Promise<TestSession> {
  const response = await api.get<TestSession>(`/v1/api/test-sessions/by-submission/${submissionId}`);
  return {
    ...response,
    session_id: response.id || response.session_id,
    current_part: null,
  };
}

/**
 * Get minimal session status
 *
 * @param sessionId - MongoDB session ID
 * @returns Session status info
 */
export async function getSessionStatus(sessionId: string): Promise<{
  session_id: string;
  status: string;
  current_part: string | null;
}> {
  return api.get(`/v1/api/test-sessions/${sessionId}/status`);
}
