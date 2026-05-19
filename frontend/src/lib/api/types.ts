/**
 * TypeScript types for API responses
 *
 * These should match the Pydantic schemas from the backend.
 */

// ===== ENUMS =====

export enum TestType {
  QUIZ = "QUIZ",
  INTERVIEW = "INTERVIEW",
}

export enum SubmissionStatus {
  ASSIGNED = "ASSIGNED",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  EVALUATED = "EVALUATED", // AI evaluation complete, awaiting trainer review
  GRADED = "GRADED", // Trainer has reviewed and scored
  ABANDONED = "ABANDONED",
}

export enum UserRole {
  TRAINER = "TRAINER",
  PARTICIPANT = "PARTICIPANT",
  ADMIN = "ADMIN",
}

export type QuestionType = "mcq" | "multi" | "true_false" | "text";
export type QuestionDifficulty = "easy" | "medium" | "hard";

// ===== SKILL =====

export interface SkillInfo {
  id: number;
  name: string;
  description?: string;
}

// ===== USER =====

export interface User {
  id: number;
  email: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
}

// ===== QUESTION =====

export interface QuestionOption {
  option_id: number;
  text: string;
}

export interface Question {
  id?: string; // MongoDB _id
  type: QuestionType;
  question_text: string;
  options?: QuestionOption[];
  correct_answers?: (number | boolean | string)[];
  sample_answer?: string;
  answer_explanation?: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface QuestionCreate {
  type: QuestionType;
  question_text: string;
  options?: { text: string }[]; // Backend auto-generates option_id
  correct_answers?: (number | boolean | string)[];
  sample_answer?: string;
  answer_explanation?: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags: string[];
}

export type QuestionUpdate = Partial<QuestionCreate>;

// ===== TEST =====

export interface Test {
  id: number;
  name: string;
  test_type: TestType;
  role?: string;
  curriculum?: string;
  duration_seconds?: number;
  number_of_questions?: number;
  created_by_id: number; // FK to User (database ID)
  active: boolean;
  created_at: string;
  updated_at: string;
  skills?: SkillInfo[];
  skill_ids?: number[];
}

export interface TestCreate {
  name: string;
  test_type: TestType;
  role?: string;
  curriculum?: string;
  duration_seconds?: number;
  number_of_questions?: number;
  active?: boolean;
  skill_ids?: number[];
  // Note: created_by is extracted from JWT, not in request body
}

export interface TestUpdate {
  name?: string;
  test_type?: TestType;
  role?: string;
  curriculum?: string;
  duration_seconds?: number;
  number_of_questions?: number;
  active?: boolean;
}

export interface BulkTestAssignmentCreate {
  test_id: number;
  participant_emails: string[];
  assigned_by: string;
  due_date?: string;
}

// ===== TEST SUBMISSION =====

export interface TestSubmission {
  id: number;
  test_id: number;
  user_id: number; // FK to User (participant)
  assigned_by?: number; // FK to User (trainer)
  assigned_at: string;
  due_date?: string;
  status: SubmissionStatus;
  started_at?: string;
  submitted_at?: string;
  ai_score?: number;
  trainer_score?: number;
  final_score?: number;
  feedback?: string;
  reviewed_at?: string; // When trainer reviewed
  reviewed_by_id?: number; // Trainer user ID who reviewed
  created_at: string;
  updated_at: string;
  // Optional test relationship (populated when requested with joins)
  test?: {
    id: number;
    name: string;
    test_type: 'QUIZ' | 'INTERVIEW';
    role?: string;
    curriculum?: string;
  };
  // Optional participant information (fetched from User Service)
  participant_name?: string;
  participant_email?: string;
}

export interface TestSubmissionCreate {
  test_id: number;
  user_id: number;
  due_date?: string;
  // Note: assigned_by is extracted from JWT, not in request body
}

export interface BulkTestSubmissionCreate {
  test_id: number;
  participant_emails: string[];
  due_date?: string;
  // Note: assigned_by is extracted from JWT
}

export interface TestSubmissionUpdate {
  status?: SubmissionStatus;
  started_at?: string;
  submitted_at?: string;
  ai_score?: number;
  trainer_score?: number;
  final_score?: number;
  feedback?: string;
}

// ===== DASHBOARD =====

export interface TrainerDashboardStats {
  active_tests_count: number;
  total_participants_count: number;
  pending_submissions_count: number;
  quiz_tests_count: number;
  interview_tests_count: number;
  total_submissions: number;
  completed_submissions: number;
}

export interface ParticipantDashboardStats {
  assigned_tests_count: number;
  completed_tests_count: number;
  in_progress_tests_count: number;
  average_score?: number;
  tests_due_this_week: number;
}

export interface AssignedTestInfo {
  submission_id: number; // Renamed from assignment_id
  test_id: number;
  test_name: string;
  test_type: TestType;
  duration_seconds?: number;
  role?: string;
  assigned_at: string;
  due_date?: string;
  status: SubmissionStatus;
  final_score?: number; // Renamed from score
  ai_score?: number; // AI-generated score (before trainer review)
  trainer_score?: number; // Trainer-provided score
  submitted_at?: string;
  skills: SkillInfo[];
}

export interface TrainerTestInfo {
  id: number;
  name: string;
  test_type: string;
  active: boolean;
  created_at: string;
  created_by_id?: number; // FK to User (database ID)
  duration_seconds?: number;
  total_submissions: number;
  completed_submissions: number;
  pending_submissions: number;
  role?: string;
  skills: SkillInfo[];
}

// ===== QUIZ SESSION (AI Quiz Service) =====

export interface QuizQuestion {
  question_id: string;  // MongoDB ObjectId
  question_text: string;  // AI-rephrased question
  question_type: "mcq" | "multi" | "true_false";
  difficulty: "easy" | "medium" | "hard";
  options?: {
    option_id: number;
    text: string;
  }[];
  // Note: correct_answers are NEVER sent to frontend for security (only during quiz)
}

export interface GradedQuizQuestion {
  question_id: string;  // MongoDB ObjectId
  question_text: string;  // AI-rephrased question
  question_type: "mcq" | "multi" | "true_false";
  difficulty: "easy" | "medium" | "hard";
  options?: {
    option_id: number;
    text: string;
  }[];
  selected_answers?: number[];  // User's selected option IDs
  correct_answers?: number[];  // Correct option IDs (only included when session is graded)
  is_correct?: boolean;  // Whether the answer was correct
  time_spent_seconds?: number;  // Time spent on question
}

export interface QuizAnswer {
  question_id: string;
  selected_answers: number[];  // Array of option IDs
  time_spent_seconds?: number;
}

export interface TestSessionCreate {
  test_id: number;  // SQL test ID
  submission_id: number;  // SQL submission ID
  user_id: number;
  total_questions?: number;  // Default: 20
  part_a_config?: {
    easy: number;
    medium: number;
    hard: number;
  };
}

export interface TestSessionPart {
  questions: GradedQuizQuestion[];
  started_at?: string;
  completed_at?: string;
  score?: number;
  total_questions: number;
}

export interface TestSession {
  id?: string;  // MongoDB session ID (from backend)
  session_id?: string;  // MongoDB session ID (mapped from id)
  test_id: number;
  submission_id: number;
  user_id: number;
  status: "STARTED" | "PART_A_IN_PROGRESS" | "PART_A_COMPLETED" | "PART_B_IN_PROGRESS" | "PART_B_COMPLETED" | "GRADED" | "COMPLETED";
  started_at: string;
  completed_at?: string;
  total_questions: number;
  part_a_config?: {
    easy: number;
    medium: number;
    hard: number;
  };
  part_b_config?: {
    easy: number;
    medium: number;
    hard: number;
  };
  part_a?: TestSessionPart;
  part_b?: TestSessionPart;
  total_score?: number;
  percentage_score?: number;
  ai_model_used?: string;  // AI model used for evaluation (set by Lambda)
  evaluation_metadata?: {
    evaluation_timestamp?: string;
    algorithm_version?: string;
    audit_log?: {
      part_a_scoring?: Record<string, any>;
      part_b_scoring?: Record<string, any>;
      difficulty_weights?: Record<string, number>;
      score_calculation?: Record<string, any>;
      final_score?: Record<string, any>;
      fairness_notes?: string;
    };
  };  // AI evaluation metadata including audit log and scoring details (set by Lambda)
  created_at: string;
  updated_at: string;
  // Legacy fields for backwards compatibility
  current_part?: "A" | "B" | null;
}

export interface PartAQuestionsResponse {
  session_id: string;
  questions: QuizQuestion[];
  total_questions: number;
  time_limit_minutes?: number;
}

export interface PartBQuestionsResponse {
  session_id: string;
  questions: QuizQuestion[];
  total_questions: number;
  time_limit_minutes?: number;
  ai_message?: string;  // Adaptive feedback message
}

export interface PartAAnswersSubmit {
  session_id: string;
  answers: QuizAnswer[];
}

export interface PartBAnswersSubmit {
  session_id: string;
  answers: QuizAnswer[];
}

export interface QuizSubmitResponse {
  score: number;
  total_questions: number;
  correct_answers: number;
  analysis?: string;
}

// ===== TYPE ALIASES (for backwards compatibility) =====

/** @deprecated Use SubmissionStatus instead */
export const TestAssignmentStatus = SubmissionStatus;

/** @deprecated Use TestSubmission instead */
export type TestAssignment = TestSubmission;

/** @deprecated Use ParticipantDashboardStats instead */
export type AssociateDashboardStats = ParticipantDashboardStats;
