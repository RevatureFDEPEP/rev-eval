/**
 * Dashboard API
 *
 * Functions for fetching dashboard statistics and data.
 * Aggregates data from CRUD endpoints (tests and submissions).
 *
 * Works in both server and client components.
 */

import { getTests } from './tests';
import { getSubmissions } from './submissions';
import {
  TrainerDashboardStats,
  ParticipantDashboardStats,
  AssignedTestInfo,
  TrainerTestInfo,
  TestType,
  SubmissionStatus,
} from './types';

/**
 * Get trainer dashboard statistics
 * Aggregates data from tests and submissions endpoints
 */
export async function getTrainerDashboardStats(): Promise<TrainerDashboardStats> {
  // Fetch all tests and submissions in parallel
  const [tests, submissions] = await Promise.all([
    getTests(),
    getSubmissions(),
  ]);

  // Filter active tests only
  const activeTests = tests.filter(t => t.active);

  // Calculate statistics
  const active_tests_count = activeTests.length;
  const quiz_tests_count = activeTests.filter(t => t.test_type === TestType.QUIZ).length;
  const interview_tests_count = activeTests.filter(t => t.test_type === TestType.INTERVIEW).length;

  const total_submissions = submissions.length;
  const pending_submissions_count = submissions.filter(
    s => s.status === SubmissionStatus.ASSIGNED
  ).length;
  const completed_submissions = submissions.filter(
    s => s.status === SubmissionStatus.COMPLETED
  ).length;

  // Get unique participant count
  const uniqueParticipants = new Set(submissions.map(s => s.user_id));
  const total_participants_count = uniqueParticipants.size;

  return {
    active_tests_count,
    total_participants_count,
    pending_submissions_count,
    quiz_tests_count,
    interview_tests_count,
    total_submissions,
    completed_submissions,
  };
}

/**
 * Get participant dashboard statistics
 * Aggregates data from submissions endpoint filtered by current user
 *
 * Note: Backend automatically filters submissions by authenticated user for participants
 */
export async function getParticipantDashboardStats(): Promise<ParticipantDashboardStats> {
  // Fetch submissions (backend automatically filters by authenticated user for participants)
  const submissions = await getSubmissions();

  const assigned_tests_count = submissions.length;
  // Count both COMPLETED (user finished) and GRADED (evaluation complete) as completed
  const completed_tests_count = submissions.filter(
    s => s.status === SubmissionStatus.COMPLETED || s.status === SubmissionStatus.GRADED
  ).length;
  const in_progress_tests_count = submissions.filter(
    s => s.status === SubmissionStatus.IN_PROGRESS
  ).length;

  // Calculate average score - only use GRADED tests (they have scores)
  const gradedWithScores = submissions.filter(
    s => s.status === SubmissionStatus.GRADED && 
         (s.final_score !== null && s.final_score !== undefined || s.ai_score !== null && s.ai_score !== undefined)
  );
  const average_score = gradedWithScores.length > 0
    ? gradedWithScores.reduce((sum, s) => sum + (s.final_score ?? s.ai_score ?? 0), 0) / gradedWithScores.length
    : undefined;

  // Tests due this week (exclude completed/graded/abandoned tests)
  const now = new Date();
  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  const tests_due_this_week = submissions.filter(s => {
    if (!s.due_date || 
        s.status === SubmissionStatus.COMPLETED || 
        s.status === SubmissionStatus.GRADED || 
        s.status === SubmissionStatus.ABANDONED) return false;
    const dueDate = new Date(s.due_date);
    return dueDate >= now && dueDate <= weekFromNow;
  }).length;

  return {
    assigned_tests_count,
    completed_tests_count,
    in_progress_tests_count,
    average_score,
    tests_due_this_week,
  };
}

/** @deprecated Use getParticipantDashboardStats instead */
export const getAssociateDashboardStats = getParticipantDashboardStats;

/**
 * Get list of tests assigned to current participant
 * Returns submissions with test details
 *
 * Note: Backend automatically filters submissions by authenticated user for participants
 */
export async function getAssignedTests(): Promise<AssignedTestInfo[]> {
  // Fetch submissions (backend filters by user for participants) and all tests
  const [submissions, tests] = await Promise.all([
    getSubmissions(),
    getTests(),
  ]);

  // Create a map of test_id to test details
  const testMap = new Map(tests.map(t => [t.id, t]));

  // Map submissions to AssignedTestInfo
  const assignedTests: AssignedTestInfo[] = submissions.map(submission => {
    const test = testMap.get(submission.test_id);
    // Use final_score if available, otherwise fall back to ai_score
    const displayScore = submission.final_score ?? submission.ai_score;
    return {
      submission_id: submission.id,
      test_id: submission.test_id,
      test_name: test?.name || 'Unknown Test',
      test_type: test?.test_type || TestType.QUIZ,
      duration_seconds: test?.duration_seconds,
      role: test?.role,
      assigned_at: submission.assigned_at,
      due_date: submission.due_date,
      status: submission.status,
      final_score: displayScore,
      submitted_at: submission.submitted_at,
      skills: test?.skills ?? [],
    };
  });

  // Sort by due date (earliest first), then by assigned date
  assignedTests.sort((a, b) => {
    const aDue = a.due_date ? new Date(a.due_date).getTime() : Infinity;
    const bDue = b.due_date ? new Date(b.due_date).getTime() : Infinity;
    if (aDue !== bDue) return aDue - bDue;
    return new Date(a.assigned_at).getTime() - new Date(b.assigned_at).getTime();
  });

  return assignedTests;
}

/**
 * Get list of tests created by current trainer
 * Returns tests with submission counts
 */
export async function getTrainerTests(): Promise<TrainerTestInfo[]> {
  // Fetch tests and submissions
  const [tests, submissions] = await Promise.all([
    getTests(),
    getSubmissions(),
  ]);

  // Create a map of test_id to submissions
  const submissionsByTest = new Map<number, typeof submissions>();
  submissions.forEach(submission => {
    if (!submissionsByTest.has(submission.test_id)) {
      submissionsByTest.set(submission.test_id, []);
    }
    submissionsByTest.get(submission.test_id)!.push(submission);
  });

  // Map tests to TrainerTestInfo with submission counts
  const trainerTests: TrainerTestInfo[] = tests.map(test => {
    const testSubmissions = submissionsByTest.get(test.id) || [];
    return {
      id: test.id,
      name: test.name,
      test_type: test.test_type,
      active: test.active,
      created_at: test.created_at,
      created_by_id: test.created_by_id,
      duration_seconds: test.duration_seconds,
      total_submissions: testSubmissions.length,
      completed_submissions: testSubmissions.filter(s => s.status === SubmissionStatus.COMPLETED).length,
      pending_submissions: testSubmissions.filter(s => s.status === SubmissionStatus.ASSIGNED).length,
      role: test.role,
      skills: test.skills ?? [],
    };
  });

  // Sort by created_at (newest first)
  trainerTests.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return trainerTests;
}
