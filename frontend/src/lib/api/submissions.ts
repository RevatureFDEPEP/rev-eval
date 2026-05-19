/**
 * Test Submissions API
 *
 * Functions for managing test submissions and assignments.
 */

import { api } from './client';
import {
  TestSubmission,
  TestSubmissionCreate,
  TestSubmissionUpdate,
  BulkTestSubmissionCreate,
} from './types';

/**
 * Get all submissions (with optional filters)
 *
 * @param params - Optional filters
 * @param params.test_id - Filter by test ID
 * @param params.user_id - Filter by user ID (returns only that user's submissions)
 * @param params.status - Filter by status
 */
export async function getSubmissions(params?: {
  test_id?: number;
  user_id?: number;
  status?: string;
}): Promise<TestSubmission[]> {
  const query = new URLSearchParams();
  if (params?.user_id !== undefined) query.append('user_id', params.user_id.toString());
  if (params?.test_id !== undefined) query.append('test_id', params.test_id.toString());
  if (params?.status) query.append('status', params.status);

  const queryString = query.toString();
  const endpoint = `/v1/api/submissions/${queryString ? `?${queryString}` : ''}`;

  return api.get<TestSubmission[]>(endpoint);
}

/**
 * Get a specific submission by ID
 */
export async function getSubmission(submissionId: number): Promise<TestSubmission> {
  return api.get<TestSubmission>(`/v1/api/submissions/${submissionId}/`);
}

/**
 * Create a new submission (assign test to participant)
 */
export async function createSubmission(data: TestSubmissionCreate): Promise<TestSubmission> {
  return api.post<TestSubmission>('/v1/api/submissions/', data);
}

/**
 * Bulk create submissions (assign test to multiple participants)
 */
export async function bulkCreateSubmissions(data: BulkTestSubmissionCreate): Promise<{
  success: number;
  failed: number;
  submissions: TestSubmission[];
}> {
  return api.post<{
    success: number;
    failed: number;
    submissions: TestSubmission[];
  }>('/v1/api/submissions/bulk-assign', data);
}

/**
 * Update a submission
 */
export async function updateSubmission(
  submissionId: number,
  data: TestSubmissionUpdate
): Promise<TestSubmission> {
  return api.put<TestSubmission>(`/v1/api/submissions/${submissionId}/`, data);
}

/**
 * Delete a submission
 */
export async function deleteSubmission(submissionId: number): Promise<void> {
  return api.delete<void>(`/v1/api/submissions/${submissionId}/`);
}

/**
 * Get EVALUATED submissions for trainer to review
 * Returns submissions for tests created by the authenticated trainer
 */
export async function getEvaluatedSubmissionsForTrainer(): Promise<TestSubmission[]> {
  return api.get<TestSubmission[]>('/v1/api/submissions/trainer/evaluated');
}

/**
 * Get GRADED submissions (already reviewed by trainer)
 * Returns submissions with GRADED status
 */
export async function getGradedSubmissions(): Promise<TestSubmission[]> {
  return api.get<TestSubmission[]>('/v1/api/submissions/graded');
}

/**
 * Get ALL submissions for trainer across all statuses
 * Returns submissions for tests created by the authenticated trainer
 * Includes ASSIGNED, IN_PROGRESS, COMPLETED, EVALUATED, GRADED, ABANDONED
 * Includes both QUIZ and INTERVIEW test types
 */
export async function getAllSubmissionsForTrainer(): Promise<TestSubmission[]> {
  return api.get<TestSubmission[]>('/v1/api/submissions/trainer/all');
}

/**
 * Get full review details for a submission
 * Includes submission, test info, transcript, and AI evaluation
 */
export async function getSubmissionReviewDetails(submissionId: number): Promise<{
  submission: TestSubmission;
  test: {
    id: number;
    name: string;
    test_type: string;
    role?: string;
    curriculum?: string;
    duration_seconds?: number;
    skills: Array<{ id: number; name: string; description?: string }>;
  };
  transcript: any; // Full transcript from interview service
}> {
  return api.get(`/v1/api/submissions/${submissionId}/review-details`);
}

/**
 * Submit trainer review and score
 */
export async function submitTrainerReview(
  submissionId: number,
  data: {
    trainer_score: number;
    feedback?: string;
    trainer_evaluation?: any;  // Comprehensive trainer evaluation structure
  }
): Promise<{
  submission_id: number;
  trainer_score: number;
  final_score: number;
  ai_score?: number;
  feedback?: string;
  reviewed_at: string;
  reviewed_by_id: number;
  status: string;
}> {
  return api.post(`/v1/api/submissions/${submissionId}/trainer-review`, data);
}
