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
 * Request a pre-signed POST policy for uploading a question image to MinIO.
 * Trainer only (enforced server-side via the gateway-injected role).
 */
export async function getPresignedUpload(
  contentType: string
): Promise<PresignedUpload> {
  return api.get<PresignedUpload>(
    `/v1/api/questions/presigned-upload-url?content_type=${encodeURIComponent(
      contentType
    )}`
  );
}

/**
 * Upload a file directly to MinIO using a pre-signed POST policy.
 *
 * This bypasses the BFF/gateway by design — the request goes straight to
 * MinIO with no cookies or Bearer token. The policy's form `fields` (including
 * `key` and `Content-Type`) must be appended before the file, and the size
 * ceiling is enforced by the policy itself.
 *
 * @returns the object key to persist on the question.
 */
export async function uploadToPresignedPost(
  presigned: PresignedUpload,
  file: File
): Promise<string> {
  const form = new FormData();
  Object.entries(presigned.fields).forEach(([k, v]) => form.append(k, v));
  form.append('file', file);

  const res = await fetch(presigned.url, { method: 'POST', body: form });
  if (!res.ok) {
    throw new Error(`Image upload failed (${res.status})`);
  }
  return presigned.object_key;
}
