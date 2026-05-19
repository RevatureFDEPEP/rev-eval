/**
 * Interview API
 *
 * Functions for fetching interview transcripts and evaluation data.
 */

import { api } from './client';

export interface InterviewMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

// Per-question evaluation from interview agent
export interface InterviewEvaluation {
  score: number;
  strengths: string;
  weaknesses: string;
  overall: string;
  question: string;
  answer: string;
}

// Skill-specific evaluation from Lambda
export interface SkillEvaluation {
  score: number;
  feedback: string;
  proficiency_level: 'EXPERT' | 'PROFICIENT' | 'COMPETENT' | 'BASIC' | 'INSUFFICIENT';
}

// Final Lambda evaluation (comprehensive)
export interface LambdaEvaluation {
  overall_score: number;
  score_breakdown: {
    technical_knowledge: number;
    problem_solving: number;
    communication: number;
    code_quality: number;
    engagement: number;
  };
  skill_breakdown: Record<string, SkillEvaluation>;
  feedback: string;
  strengths: string[];
  improvements: string[];
  key_highlights: string[];
  red_flags: string[];
  recommendation: 'STRONG_HIRE' | 'HIRE' | 'MAYBE' | 'NO_HIRE';
  reasoning: string;
  evaluated_at?: string;
  evaluated_by?: string;
}

export interface InterviewTranscript {
  session_id: string;
  submission_id: number;
  test_name: string;
  test_role?: string;
  messages: InterviewMessage[];
  message_count: number;
  duration_seconds?: number;
  status: string;
  created_at: string;
  ended_at?: string;
  // Per-question evaluations from interview agent
  evaluations?: InterviewEvaluation[];
  average_score?: number;
  total_score?: number;
  total_questions?: number;
  // Final Lambda evaluation (if graded)
  lambda_evaluation?: LambdaEvaluation;
}

/**
 * Get interview transcript for a submission
 *
 * Returns the full conversation transcript with evaluation data.
 *
 * Note: This goes through API Gateway which routes to interview service.
 */
export async function getInterviewTranscript(submissionId: number): Promise<InterviewTranscript> {
  // Call through Next.js API route (BFF) -> API Gateway -> Interview Service
  return api.get<InterviewTranscript>(`/v1/api/interview/submissions/${submissionId}/transcript`);
}

/**
 * Upload audio for an interview message to S3
 *
 * @param sessionId - Interview session ID
 * @param messageIndex - Index of the message in the conversation (0-based)
 * @param audioBlob - Audio file as Blob (WebM format)
 * @returns Audio URL in S3
 */
export async function uploadInterviewAudio(
  sessionId: string,
  messageIndex: number,
  audioBlob: Blob
): Promise<string> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('message_index', messageIndex.toString());
  formData.append('audio', audioBlob, 'audio.webm');

  const response = await fetch('/api/interview/upload-audio', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to upload audio: ${error}`);
  }

  const data = await response.json();
  return data.audio_url;
}

