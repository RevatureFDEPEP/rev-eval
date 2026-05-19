/**
 * Tests API
 *
 * Functions for managing tests and assignments.
 */

import { api } from './client';
import {
  Test,
  TestCreate,
  TestUpdate,
  BulkTestAssignmentCreate,
  TestAssignment,
} from './types';

/**
 * Create a new test
 */
export async function createTest(data: TestCreate): Promise<Test> {
  return api.post<Test>('/v1/api/tests', data);
}

/**
 * Get all tests
 */
export async function getTests(): Promise<Test[]> {
  return api.get<Test[]>('/v1/api/tests');
}

/**
 * Get a specific test by ID
 */
export async function getTest(testId: number): Promise<Test> {
  return api.get<Test>(`/v1/api/tests/${testId}`);
}

/**
 * Update a test
 */
export async function updateTest(testId: number, data: TestUpdate): Promise<Test> {
  return api.put<Test>(`/v1/api/tests/${testId}`, data);
}

/**
 * Delete a test
 */
export async function deleteTest(testId: number): Promise<void> {
  return api.delete<void>(`/v1/api/tests/${testId}`);
}

/**
 * Bulk assign test to multiple participants
 * Note: assigned_by is automatically extracted from JWT by the backend
 */
export async function bulkAssignTest(data: BulkTestAssignmentCreate): Promise<{
  success_count: number;
  failure_count: number;
  created_submissions: any[];
  errors: any[];
}> {
  return api.post<{
    success_count: number;
    failure_count: number;
    created_submissions: any[];
    errors: any[];
  }>('/v1/api/submissions/bulk-assign', {
    test_id: data.test_id,
    participant_emails: data.participant_emails,
    due_date: data.due_date,
    // assigned_by_id is automatically extracted from JWT token by the backend
  });
}

/**
 * Add a single participant to a test
 */
export async function addParticipant(testId: number, email: string): Promise<Test> {
  return api.post<Test>(`/v1/api/tests/${testId}/participants`, { email });
}

/**
 * Remove a participant from a test
 */
export async function removeParticipant(testId: number, email: string): Promise<void> {
  return api.delete<void>(`/v1/api/tests/${testId}/participants/${email}`);
}
