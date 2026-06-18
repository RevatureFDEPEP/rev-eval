/**
 * Questions API Client
 *
 * Handles all question-related API calls.
 */

import { api } from './client';
import { Question, QuestionCreate, QuestionUpdate } from './types';

// MongoDB returns _id; map it to id so callers use question.id consistently
function normalizeQuestion(q: Question & { _id?: string }): Question {
  return { ...q, id: q.id ?? q._id };
}

export async function getQuestions(): Promise<Question[]> {
  const data = await api.get<(Question & { _id?: string })[]>('/v1/api/questions');
  return data.map(normalizeQuestion);
}

export async function getQuestion(id: string): Promise<Question> {
  const data = await api.get<Question & { _id?: string }>(`/v1/api/questions/${id}`);
  return normalizeQuestion(data);
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
