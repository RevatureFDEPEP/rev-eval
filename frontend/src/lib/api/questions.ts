/**
 * Questions API Client
 *
 * Handles all question-related API calls.
 */

import { api } from './client';
import { PresignedUpload, Question, QuestionCreate, QuestionUpdate } from './types';

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

/**
 * Get a pre-signed PUT URL for uploading a question image to MinIO
 */
export async function getPresignedUploadUrl(
  contentType: string
): Promise<PresignedUpload> {
  return api.get<PresignedUpload>(
    `/v1/api/questions/presigned-upload-url?content_type=${encodeURIComponent(contentType)}`
  );
}

/**
 * Upload a file directly to MinIO via a pre-signed PUT URL.
 *
 * Deliberately bypasses the api/BFF client: the request goes straight to
 * MinIO with no cookies or Bearer token. The Content-Type header must match
 * the signed content type exactly or MinIO rejects the signature.
 */
export async function uploadToPresignedUrl(
  uploadUrl: string,
  file: File
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': file.type },
  });
  if (!res.ok) {
    throw new Error(`Image upload failed (${res.status})`);
  }
}
