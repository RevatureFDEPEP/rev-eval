/**
 * Questions API Client
 *
 * Handles all question-related API calls.
 */

import { api } from './client';
import { Question, QuestionCreate, QuestionUpdate } from './types';

/**
 * Get all questions
 */
export async function getQuestions(): Promise<Question[]> {
  return api.get<Question[]>('/v1/api/questions');
}

/**
 * Get a single question by ID
 */
export async function getQuestion(id: string): Promise<Question> {
  return api.get<Question>(`/v1/api/questions/${id}`);
}

/**
 * Create a new question
 */
export async function createQuestion(data: QuestionCreate): Promise<Question> {
  return api.post<Question>('/v1/api/questions', data);
}

/**
 * Update an existing question
 */
export async function updateQuestion(
  id: string,
  data: QuestionUpdate
): Promise<Question> {
  return api.put<Question>(`/v1/api/questions/${id}`, data);
}

/**
 * Delete a question
 */
export async function deleteQuestion(id: string): Promise<void> {
  return api.delete<void>(`/v1/api/questions/${id}`);
}
