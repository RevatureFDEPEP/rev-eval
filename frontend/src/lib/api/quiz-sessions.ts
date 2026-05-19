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
  const response = await api.post<any>('/v1/api/test-sessions/', data);

  return {
    id: response.id,
    session_id: response.id,  // Map 'id' to 'session_id' for backwards compatibility
    test_id: response.test_id,
    submission_id: response.submission_id,
    user_id: response.user_id,
    status: response.status,
    started_at: response.started_at,
    completed_at: response.completed_at,
    total_questions: response.total_questions,
    part_a_config: response.part_a_config,
    part_b_config: response.part_b_config,
    part_a: response.part_a,
    part_b: response.part_b,
    total_score: response.total_score,
    percentage_score: response.percentage_score,
    created_at: response.created_at,
    updated_at: response.updated_at,
    current_part: null,  // Not in backend response, infer from status
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
  const response = await api.get<any>(`/v1/api/test-sessions/${sessionId}`);
  // Map 'id' to 'session_id' for backwards compatibility
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
  const response = await api.get<any>(`/v1/api/test-sessions/by-submission/${submissionId}`);
  // Map 'id' to 'session_id' for backwards compatibility and ensure all fields are properly mapped
  return {
    id: response.id,
    session_id: response.id || response.session_id,
    test_id: response.test_id,
    submission_id: response.submission_id,
    user_id: response.user_id,
    status: response.status,
    started_at: response.started_at,
    completed_at: response.completed_at,
    total_questions: response.total_questions,
    part_a_config: response.part_a_config,
    part_b_config: response.part_b_config,
    part_a: response.part_a,
    part_b: response.part_b,
    total_score: response.total_score,
    percentage_score: response.percentage_score,
    created_at: response.created_at,
    updated_at: response.updated_at,
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
