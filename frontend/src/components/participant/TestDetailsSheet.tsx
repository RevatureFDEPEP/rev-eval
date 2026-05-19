"use client";

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AssignedTestInfo, TestSession, GradedQuizQuestion } from '@/lib/api/types';
import { getTestSessionBySubmission } from '@/lib/api/quiz-sessions';

// Interview-transcript surface was removed in the PEP brownfield strip
// (ai-interview-service is Phase 2). Candidates rebuild this on W3 D13–D14.
interface InterviewTranscriptMessage {
  speaker?: string;
  text?: string;
  timestamp?: string;
}

interface InterviewTranscriptEvaluation {
  overall_score: number;
  score_breakdown: Record<string, number>;
  skill_breakdown: Record<string, { score?: number }>;
  feedback?: string;
  strengths?: string[];
  improvements?: string[];
  evaluated_at?: string;
  evaluated_by?: string;
}

interface InterviewTranscript {
  messages: InterviewTranscriptMessage[];
  lambda_evaluation?: InterviewTranscriptEvaluation;
}

async function getInterviewTranscript(_submissionId: number): Promise<InterviewTranscript> {
  throw new Error('Interview transcripts not available — candidate-built on W3 D13.');
}
import { formatTableDate } from '@/lib/utils/date';
import { Award, CalendarDays, CheckCircle2, Clock, FileText, MessageSquare, TrendingUp, CheckCircle, XCircle } from 'lucide-react';

interface ParticipantTestDetailsSheetProps {
  test: AssignedTestInfo | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const statusLabels: Record<string, string> = {
  ASSIGNED: 'Assigned',
  IN_PROGRESS: 'In Progress',
  COMPLETED: 'Pending Review',
  EVALUATED: 'Pending Review',
  GRADED: 'Graded',
  ABANDONED: 'Abandoned',
};

const statusVariants: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  ASSIGNED: 'default',
  IN_PROGRESS: 'outline',
  COMPLETED: 'secondary',
  EVALUATED: 'secondary',
  GRADED: 'secondary',  // Same as COMPLETED since it's a completed state with score
  ABANDONED: 'destructive',
};

export function ParticipantTestDetailsSheet({ test, open, onOpenChange }: ParticipantTestDetailsSheetProps) {
  const [transcript, setTranscript] = useState<InterviewTranscript | null>(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [quizSession, setQuizSession] = useState<TestSession | null>(null);
  const [loadingQuizSession, setLoadingQuizSession] = useState(false);
  const [quizSessionError, setQuizSessionError] = useState<string | null>(null);

  // Compute derived values (use optional chaining to handle null test)
  const isQuiz = test ? ((test.test_type as string) === 'QUIZ' || (test.test_type as string) === 'MCQ') : false;
  const testType = isQuiz ? 'Quiz' : 'Interview';
  const durationLabel = test?.duration_seconds ? `${Math.round(test.duration_seconds / 60)} minutes` : 'No time limit';
  const assignedOn = test ? formatTableDate(test.assigned_at) : '';
  const dueOn = test ? (formatTableDate(test.due_date) || 'No due date') : 'No due date';
  const completedOn = test ? (formatTableDate(test.submitted_at) || 'Not submitted') : 'Not submitted';
  // Handle score display - use final_score if available, otherwise ai_score, otherwise show pending
  const displayScore = test ? (test.final_score ?? test.ai_score ?? null) : null;
  const scoreLabel = displayScore != null ? `${Math.round(displayScore)}%` : 'Pending';
  const hasSkills = test ? (Array.isArray(test.skills) && test.skills.length > 0) : false;
  // COMPLETED = user finished test, GRADED = evaluation complete with score
  const isCompleted = test?.status === 'COMPLETED' || test?.status === 'GRADED';
  const isGraded = test?.status === 'GRADED';
  const submissionId = test?.submission_id;

  // Fetch transcript for completed interviews
  // This useEffect always runs (hooks must be called unconditionally)
  useEffect(() => {
    // Early return inside useEffect is fine - the hook itself is always called
    if (!test || !open || isQuiz || !isCompleted || !submissionId || transcript || loadingTranscript) {
      return;
    }

    setLoadingTranscript(true);
    setTranscriptError(null);
    getInterviewTranscript(submissionId)
      .then((data) => {
        setTranscript(data);
        setLoadingTranscript(false);
      })
      .catch((err) => {
        console.error('Failed to load transcript:', err);
        setTranscriptError(err instanceof Error ? err.message : 'Failed to load transcript');
        setLoadingTranscript(false);
      });
  }, [test, open, isQuiz, isCompleted, submissionId, transcript, loadingTranscript]);

  // Fetch quiz session data for completed/graded quizzes
  useEffect(() => {
    if (!test || !open || !isQuiz || !isCompleted || !submissionId || quizSession || loadingQuizSession) {
      return;
    }

    setLoadingQuizSession(true);
    setQuizSessionError(null);
    getTestSessionBySubmission(submissionId)
      .then((data) => {
        console.log('📊 Quiz session data received:', {
          part_a: data.part_a,
          part_b: data.part_b,
          part_a_score: data.part_a?.score,
          part_b_score: data.part_b?.score,
          part_a_questions_count: data.part_a?.questions?.length,
          part_b_questions_count: data.part_b?.questions?.length,
        });
        setQuizSession(data);
        setLoadingQuizSession(false);
      })
      .catch((err) => {
        console.error('Failed to load quiz session:', err);
        setQuizSessionError(err instanceof Error ? err.message : 'Failed to load quiz session');
        setLoadingQuizSession(false);
      });
  }, [test, open, isQuiz, isCompleted, submissionId, quizSession, loadingQuizSession]);

  // Early return check - AFTER all hooks
  if (!test) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[70vw]"
      >
        <SheetTitle className="sr-only">Test details for {test.test_name}</SheetTitle>
        <div className="space-y-6 px-4 sm:px-6 pb-12 pt-4">
          <header className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={isQuiz ? 'default' : 'secondary'}>{testType}</Badge>
              <Badge variant={statusVariants[test.status] ?? 'default'}>{statusLabels[test.status] ?? test.status}</Badge>
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">{test.test_name}</h2>
            <p className="text-sm text-slate-500">
              {test.role ? `Designed for ${test.role}` : 'General assessment'} · {durationLabel}
            </p>
          </header>

          <Card className="border border-purple-100/70 bg-white/95 shadow-sm">
            <CardHeader>
              <CardTitle>Overview</CardTitle>
              <CardDescription>Your performance snapshot</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-600">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-500">
                  <Clock className="size-4 text-purple-400" /> Duration
                </span>
                <span className="font-medium text-slate-900">{durationLabel}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-500">
                  <Award className="size-4 text-purple-400" /> Score
                </span>
                <span className="font-medium text-slate-900">{scoreLabel}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-500">
                  <CheckCircle2 className="size-4 text-purple-400" /> Status
                </span>
                <span className="font-medium text-slate-900">{statusLabels[test.status] ?? test.status}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
              <CardDescription>Key milestones for this test</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-600">
              <div>
                <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                  <CalendarDays className="size-4 text-purple-400" /> Assigned
                </p>
                <p className="font-medium text-slate-900">{assignedOn}</p>
              </div>
              <div>
                <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                  <CalendarDays className="size-4 text-purple-400" /> Due
                </p>
                <p className="font-medium text-slate-900">{dueOn}</p>
              </div>
              <div>
                <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                  <CalendarDays className="size-4 text-purple-400" /> Completed
                </p>
                <p className="font-medium text-slate-900">{completedOn}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-orange-100/80 bg-white/95 shadow-sm">
            <CardHeader>
              <CardTitle>Skills</CardTitle>
              <CardDescription>
                {hasSkills ? 'Competencies assessed during this test' : 'No skills were linked to this test'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {hasSkills ? (
                <div className="flex flex-wrap gap-2">
                  {test.skills.map((skill) => (
                    <Badge key={skill.id} variant="secondary" className="rounded-full px-3 py-1 text-xs">
                      {skill.name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Skill tags will appear here once your trainer assigns them.</p>
              )}
            </CardContent>
          </Card>

          {/* Evaluation and Transcript Section (for completed tests) */}
          {isCompleted && (
            <Card className="border border-blue-100/80 bg-white/95 shadow-sm">
              <CardHeader>
                <CardTitle>Results & Evaluation</CardTitle>
                <CardDescription>
                  {isQuiz ? 'Quiz evaluation details' : 'Interview transcript and AI evaluation'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isQuiz ? (
                  // Quiz: Show detailed results with questions
                  <div className="space-y-4">
                    {loadingQuizSession ? (
                      <div className="flex items-center justify-center py-8 text-sm text-slate-500">
                        Loading quiz results...
                      </div>
                    ) : quizSessionError ? (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                        {quizSessionError}
                      </div>
                    ) : quizSession ? (
                      <Tabs defaultValue="overview" className="w-full">
                        <TabsList className="grid w-full grid-cols-4">
                          <TabsTrigger value="overview">Overview</TabsTrigger>
                          <TabsTrigger value="part-a">Part A</TabsTrigger>
                          <TabsTrigger value="part-b">Part B</TabsTrigger>
                          <TabsTrigger value="evaluation">Evaluation</TabsTrigger>
                        </TabsList>
                        <TabsContent value="overview" className="mt-4 space-y-3 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500">Final Score</span>
                            <span className="font-semibold text-slate-900">{scoreLabel}</span>
                          </div>
                          {quizSession.part_a && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Part A Score</span>
                              <span className="font-medium text-slate-900">
                                {quizSession.part_a.score != null
                                  ? `${quizSession.part_a.score}/${quizSession.part_a.total_questions}`
                                  : '—'}
                              </span>
                            </div>
                          )}
                          {quizSession.part_b && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Part B Score</span>
                              <span className="font-medium text-slate-900">
                                {quizSession.part_b.score != null
                                  ? `${quizSession.part_b.score}/${quizSession.part_b.total_questions}`
                                  : '—'}
                              </span>
                            </div>
                          )}
                          {isGraded && displayScore != null ? (
                            <p className="text-xs text-slate-500">
                              Your quiz has been automatically graded. Review your answers below.
                            </p>
                          ) : (
                            <p className="text-xs text-amber-600">
                              Your quiz is being evaluated. The score will appear here once grading is complete.
                            </p>
                          )}
                        </TabsContent>
                        <TabsContent value="part-a" className="mt-4">
                          {quizSession.part_a && quizSession.part_a.questions.length > 0 ? (
                            <ScrollArea className="h-[500px]">
                              <div className="space-y-4">
                                {quizSession.part_a.questions.map((question, index) => (
                                  <QuestionResultCard key={question.question_id} question={question} index={index + 1} />
                                ))}
                              </div>
                            </ScrollArea>
                          ) : (
                            <div className="flex items-center justify-center py-8 text-sm text-slate-500">
                              No Part A questions available
                            </div>
                          )}
                        </TabsContent>
                        <TabsContent value="part-b" className="mt-4">
                          {quizSession.part_b && quizSession.part_b.questions && quizSession.part_b.questions.length > 0 ? (
                            <ScrollArea className="h-[500px]">
                              <div className="space-y-4">
                                {quizSession.part_b.questions.map((question, index) => (
                                  <QuestionResultCard key={question.question_id} question={question} index={index + 1} />
                                ))}
                              </div>
                            </ScrollArea>
                          ) : (
                            <div className="flex items-center justify-center py-8 text-sm text-slate-500">
                              {quizSession.part_b
                                ? `No Part B questions available (total_questions: ${quizSession.part_b.total_questions}, questions array: ${quizSession.part_b.questions?.length ?? 'null'})`
                                : 'Part B data not available'}
                            </div>
                          )}
                        </TabsContent>
                        <TabsContent value="evaluation" className="mt-4">
                          {quizSession.evaluation_metadata ? (
                            <ScrollArea className="h-[500px]">
                              <div className="space-y-4 pr-4">
                                {/* Evaluation Info */}
                                <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
                                  <h4 className="mb-2 text-sm font-semibold text-blue-900">Evaluation Information</h4>
                                  <div className="space-y-2 text-sm">
                                    {quizSession.ai_model_used && (
                                      <div className="flex items-center justify-between">
                                        <span className="text-slate-600">AI Model Used</span>
                                        <span className="font-medium text-slate-900">{quizSession.ai_model_used}</span>
                                      </div>
                                    )}
                                    {quizSession.evaluation_metadata.algorithm_version && (
                                      <div className="flex items-center justify-between">
                                        <span className="text-slate-600">Algorithm Version</span>
                                        <span className="font-medium text-slate-900">{quizSession.evaluation_metadata.algorithm_version}</span>
                                      </div>
                                    )}
                                    {quizSession.evaluation_metadata.evaluation_timestamp && (
                                      <div className="flex items-center justify-between">
                                        <span className="text-slate-600">Evaluated At</span>
                                        <span className="font-medium text-slate-900">
                                          {new Date(quizSession.evaluation_metadata.evaluation_timestamp).toLocaleString()}
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                {/* Audit Log */}
                                {quizSession.evaluation_metadata.audit_log && (
                                  <>
                                    {/* Difficulty Weights */}
                                    {quizSession.evaluation_metadata.audit_log.difficulty_weights && (
                                      <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-4">
                                        <h4 className="mb-2 text-sm font-semibold text-purple-900">Difficulty Weights</h4>
                                        <div className="space-y-2 text-sm">
                                          {Object.entries(quizSession.evaluation_metadata.audit_log.difficulty_weights).map(([difficulty, weight]) => (
                                            <div key={difficulty} className="flex items-center justify-between">
                                              <span className="capitalize text-slate-600">{difficulty}</span>
                                              <span className="font-medium text-slate-900">{weight}x</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Part A Scoring */}
                                    {quizSession.evaluation_metadata.audit_log.part_a_scoring && (
                                      <div className="rounded-lg border border-green-200 bg-green-50/50 p-4">
                                        <h4 className="mb-2 text-sm font-semibold text-green-900">Part A Scoring</h4>
                                        <div className="space-y-2 text-sm text-slate-700">
                                          <pre className="whitespace-pre-wrap rounded bg-white p-2 text-xs font-mono">
                                            {JSON.stringify(quizSession.evaluation_metadata.audit_log.part_a_scoring, null, 2)}
                                          </pre>
                                        </div>
                                      </div>
                                    )}

                                    {/* Part B Scoring */}
                                    {quizSession.evaluation_metadata.audit_log.part_b_scoring && (
                                      <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
                                        <h4 className="mb-2 text-sm font-semibold text-blue-900">Part B Scoring</h4>
                                        <div className="space-y-2 text-sm text-slate-700">
                                          <pre className="whitespace-pre-wrap rounded bg-white p-2 text-xs font-mono">
                                            {JSON.stringify(quizSession.evaluation_metadata.audit_log.part_b_scoring, null, 2)}
                                          </pre>
                                        </div>
                                      </div>
                                    )}

                                    {/* Final Score Calculation */}
                                    {quizSession.evaluation_metadata.audit_log.final_score && (
                                      <div className="rounded-lg border border-orange-200 bg-orange-50/50 p-4">
                                        <h4 className="mb-2 text-sm font-semibold text-orange-900">Final Score Calculation</h4>
                                        <div className="space-y-2 text-sm text-slate-700">
                                          <pre className="whitespace-pre-wrap rounded bg-white p-2 text-xs font-mono">
                                            {JSON.stringify(quizSession.evaluation_metadata.audit_log.final_score, null, 2)}
                                          </pre>
                                        </div>
                                      </div>
                                    )}

                                    {/* Fairness Notes */}
                                    {quizSession.evaluation_metadata.audit_log.fairness_notes && (
                                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                        <h4 className="mb-2 text-sm font-semibold text-slate-900">Fairness Notes</h4>
                                        <p className="text-sm text-slate-700 leading-relaxed">
                                          {quizSession.evaluation_metadata.audit_log.fairness_notes}
                                        </p>
                                      </div>
                                    )}
                                  </>
                                )}
                              </div>
                            </ScrollArea>
                          ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                              <div className="mb-3 rounded-full bg-slate-100 p-4">
                                <FileText className="h-8 w-8 text-slate-400" />
                              </div>
                              <p className="text-sm font-medium text-slate-700">No evaluation metadata available</p>
                              <p className="text-xs text-slate-500 mt-1">
                                {isGraded
                                  ? 'Evaluation metadata was not generated for this quiz.'
                                  : 'Complete the quiz to receive detailed evaluation data.'}
                              </p>
                            </div>
                          )}
                        </TabsContent>
                      </Tabs>
                    ) : (
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Final Score</span>
                      <span className="font-semibold text-slate-900">{scoreLabel}</span>
                    </div>
                    {isGraded && displayScore != null ? (
                      <p className="text-xs text-slate-500">
                        Your quiz has been automatically graded. Detailed evaluation is available to your trainer.
                      </p>
                    ) : (
                      <p className="text-xs text-amber-600">
                        Your quiz is being evaluated. The score will appear here once grading is complete.
                      </p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  // Interview: Show transcript and evaluation (only show evaluation if GRADED)
                  <Tabs defaultValue="transcript" className="w-full">
                    <TabsList className={`grid w-full ${isGraded ? 'grid-cols-2' : 'grid-cols-1'}`}>
                      <TabsTrigger value="transcript">
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Transcript
                      </TabsTrigger>
                      {isGraded && (
                        <TabsTrigger value="evaluation">
                          <TrendingUp className="mr-2 h-4 w-4" />
                          Evaluation
                        </TabsTrigger>
                      )}
                    </TabsList>
                    <TabsContent value="transcript" className="mt-4">
                      {loadingTranscript ? (
                        <div className="flex items-center justify-center py-8 text-sm text-slate-500">
                          Loading transcript...
                        </div>
                      ) : transcriptError ? (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                          {transcriptError}
                        </div>
                      ) : transcript ? (
                        <ScrollArea className="h-[400px] rounded-lg border border-slate-200 bg-slate-50 p-4">
                          <div className="space-y-4">
                            {transcript.messages.map((message, index) => (
                              <div
                                key={index}
                                className={`rounded-lg p-3 ${
                                  message.role === 'assistant'
                                    ? 'bg-blue-50 border border-blue-200'
                                    : message.role === 'user'
                                      ? 'bg-green-50 border border-green-200'
                                      : 'bg-slate-50 border border-slate-200'
                                }`}
                              >
                                <div className="mb-1 flex items-center gap-2">
                                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                                    {message.role === 'assistant' ? 'AI Interviewer' : message.role === 'user' ? 'You' : 'System'}
                                  </span>
                                  {message.timestamp && (
                                    <span className="text-xs text-slate-400">
                                      {new Date(message.timestamp).toLocaleTimeString()}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm leading-relaxed text-slate-700 wrap-break-word">{message.content}</p>
                              </div>
                            ))}
                          </div>
                        </ScrollArea>
                      ) : (
                        <div className="flex items-center justify-center py-8 text-sm text-slate-500">
                          No transcript available
                        </div>
                      )}
                    </TabsContent>
                    {isGraded && (
                      <TabsContent value="evaluation" className="mt-4">
                        {transcript?.lambda_evaluation ? (
                        <ScrollArea className="h-[500px]">
                          <div className="space-y-4 pr-4">
                            {/* Overall Score Card */}
                            <div className="rounded-lg border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100/50 p-5">
                              <div className="flex items-center justify-between">
                                <span className="text-lg font-bold text-blue-900">Overall Score</span>
                                <Badge variant="default" className="bg-blue-600 text-lg px-4 py-1">
                                  {Math.round(transcript.lambda_evaluation.overall_score)}%
                                </Badge>
                              </div>
                              {test?.trainer_score && (
                                <div className="mt-3 pt-3 border-t border-blue-300">
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm font-semibold text-blue-800">Trainer Score</span>
                                    <Badge variant="secondary" className="text-base px-3 py-1">
                                      {Math.round(test.trainer_score)}%
                                    </Badge>
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Score Breakdown */}
                            <div className="rounded-lg border border-slate-200 bg-white p-4">
                              <h4 className="mb-3 text-sm font-semibold text-slate-900">Performance Breakdown</h4>
                              <div className="space-y-2">
                                {Object.entries(transcript.lambda_evaluation.score_breakdown).map(([dimension, score]) => (
                                  <div key={dimension} className="flex items-center justify-between">
                                    <span className="text-sm capitalize text-slate-600">
                                      {dimension.replace('_', ' ')}
                                    </span>
                                    <div className="flex items-center gap-2">
                                      <div className="h-2 w-32 bg-slate-200 rounded-full overflow-hidden">
                                        <div
                                          className="h-full bg-blue-500 rounded-full transition-all"
                                          style={{ width: `${score}%` }}
                                        />
                                      </div>
                                      <span className="text-sm font-medium text-slate-900 w-12 text-right">{Math.round(score)}%</span>
                          </div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Skills Breakdown */}
                            {Object.keys(transcript.lambda_evaluation.skill_breakdown).length > 0 && (
                              <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-4">
                                <h4 className="mb-3 text-sm font-semibold text-purple-900">Skills Assessment</h4>
                                <div className="space-y-3">
                                  {Object.entries(transcript.lambda_evaluation.skill_breakdown).map(([skillName, skill]) => (
                                    <div key={skillName} className="rounded-lg border border-purple-200 bg-white p-3">
                                      <div className="mb-2 flex items-center justify-between">
                                        <span className="text-sm font-semibold text-slate-900">{skillName}</span>
                                        <div className="flex items-center gap-2">
                                          <Badge
                                            variant={
                                              skill.proficiency_level === 'EXPERT' || skill.proficiency_level === 'PROFICIENT' ? 'default' :
                                              skill.proficiency_level === 'COMPETENT' ? 'secondary' :
                                              skill.proficiency_level === 'BASIC' ? 'outline' : 'destructive'
                                            }
                                            className="text-xs"
                                          >
                                            {skill.proficiency_level}
                                          </Badge>
                                          <span className="text-sm font-medium text-slate-700">{Math.round(skill.score)}%</span>
                                    </div>
                                    </div>
                                      <p className="text-xs text-slate-600">{skill.feedback}</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Feedback */}
                            {transcript.lambda_evaluation.feedback && (
                              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <h4 className="mb-2 text-sm font-semibold text-slate-900">Overall Feedback</h4>
                                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                                  {transcript.lambda_evaluation.feedback}
                                </p>
                              </div>
                            )}

                            {/* Strengths */}
                            {transcript.lambda_evaluation.strengths && transcript.lambda_evaluation.strengths.length > 0 && (
                              <div className="rounded-lg border border-green-200 bg-green-50/50 p-4">
                                <h4 className="mb-2 text-sm font-semibold text-green-900 flex items-center gap-2">
                                  <CheckCircle2 className="h-4 w-4" />
                                  Strengths
                                </h4>
                                <ul className="space-y-1">
                                  {transcript.lambda_evaluation.strengths.map((strength, i) => (
                                    <li key={i} className="text-sm text-green-800 flex items-start gap-2">
                                      <span className="text-green-600 mt-1">•</span>
                                      <span>{strength}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Areas for Improvement */}
                            {transcript.lambda_evaluation.improvements && transcript.lambda_evaluation.improvements.length > 0 && (
                              <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
                                <h4 className="mb-2 text-sm font-semibold text-amber-900 flex items-center gap-2">
                                  <TrendingUp className="h-4 w-4" />
                                  Areas for Improvement
                                </h4>
                                <ul className="space-y-1">
                                  {transcript.lambda_evaluation.improvements.map((improvement, i) => (
                                    <li key={i} className="text-sm text-amber-800 flex items-start gap-2">
                                      <span className="text-amber-600 mt-1">•</span>
                                      <span>{improvement}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Evaluation Metadata */}
                            {transcript.lambda_evaluation.evaluated_at && (
                              <div className="text-xs text-slate-500 text-center pt-2 border-t">
                                Evaluated by {transcript.lambda_evaluation.evaluated_by || 'AI'} on{' '}
                                {new Date(transcript.lambda_evaluation.evaluated_at).toLocaleString()}
                              </div>
                            )}
                            </div>
                          </ScrollArea>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                          <div className="mb-3 rounded-full bg-slate-100 p-4">
                            <TrendingUp className="h-8 w-8 text-slate-400" />
                          </div>
                          <p className="text-sm font-medium text-slate-700">No evaluation available yet</p>
                          <p className="text-xs text-slate-500 mt-1">
                            {loadingTranscript
                              ? 'Loading evaluation data...'
                              : transcript?.status === 'COMPLETED'
                                ? 'Your interview is being evaluated. This may take a few minutes.'
                                : 'Complete the interview to receive your evaluation.'}
                          </p>
                        </div>
                      )}
                      </TabsContent>
                    )}
                  </Tabs>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

// Component to display individual question results
function QuestionResultCard({ question, index }: { question: GradedQuizQuestion; index: number }) {
  // Debug log to see what we're receiving
  if (index === 1) {
    console.log('🔍 First question data:', {
      question_id: question.question_id,
      is_correct: question.is_correct,
      selected_answers: question.selected_answers,
      correct_answers: question.correct_answers,
    });
  }
  
  const isCorrect = question.is_correct ?? false;
  const selectedAnswers = question.selected_answers || [];
  const correctAnswers = question.correct_answers || [];
  const difficultyColors = {
    easy: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    hard: 'bg-red-100 text-red-800 border-red-200',
  };

  const getOptionText = (optionId: number): string => {
    const option = question.options?.find((opt) => opt.option_id === optionId);
    return option?.text || `Option ${optionId}`;
  };

  return (
    <div
      className={`rounded-lg border p-4 ${
        isCorrect
          ? 'border-green-200 bg-green-50/50'
          : 'border-red-200 bg-red-50/50'
      }`}
    >
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-700">Question {index}</span>
          <Badge
            variant="outline"
            className={`text-xs ${difficultyColors[question.difficulty]}`}
          >
            {question.difficulty}
          </Badge>
          <Badge
            variant="outline"
            className="text-xs"
          >
            {question.question_type === 'mcq' ? 'MCQ' : question.question_type === 'multi' ? 'Multiple' : 'True/False'}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {isCorrect ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <XCircle className="h-5 w-5 text-red-600" />
          )}
          <span className={`text-sm font-semibold ${isCorrect ? 'text-green-700' : 'text-red-700'}`}>
            {isCorrect ? 'Correct' : 'Incorrect'}
          </span>
        </div>
      </div>

      <p className="mb-4 text-sm font-medium text-slate-900">{question.question_text}</p>

      {question.options && question.options.length > 0 && (
        <div className="space-y-2">
          {question.options.map((option) => {
            const isSelected = selectedAnswers.includes(option.option_id);
            const isCorrectAnswer = correctAnswers.includes(option.option_id);
            let bgColor = 'bg-white';
            let borderColor = 'border-slate-200';
            let textColor = 'text-slate-700';

            if (isCorrectAnswer && isSelected) {
              bgColor = 'bg-green-100';
              borderColor = 'border-green-400';
              textColor = 'text-green-900';
            } else if (isCorrectAnswer) {
              bgColor = 'bg-green-50';
              borderColor = 'border-green-300';
              textColor = 'text-green-800';
            } else if (isSelected) {
              bgColor = 'bg-red-100';
              borderColor = 'border-red-400';
              textColor = 'text-red-900';
            }

            return (
              <div
                key={option.option_id}
                className={`rounded border p-2 text-sm ${bgColor} ${borderColor} ${textColor}`}
              >
                <div className="flex items-center gap-2">
                  {isSelected && (
                    <span className="text-xs font-semibold">Your Answer</span>
                  )}
                  {isCorrectAnswer && !isSelected && (
                    <span className="text-xs font-semibold">Correct Answer</span>
                  )}
                  {isCorrectAnswer && isSelected && (
                    <span className="text-xs font-semibold">Your Answer (Correct)</span>
                  )}
                </div>
                <p className="mt-1">{option.text}</p>
              </div>
            );
          })}
        </div>
      )}

      {question.question_type === 'true_false' && (
        <div className="mt-2 space-y-2">
          <div className="text-xs text-slate-600">
            <span className="font-medium">Your Answer: </span>
            <span>{selectedAnswers.includes(1) ? 'True' : selectedAnswers.includes(2) ? 'False' : 'Not answered'}</span>
          </div>
          <div className="text-xs text-slate-600">
            <span className="font-medium">Correct Answer: </span>
            <span>{correctAnswers.includes(1) ? 'True' : correctAnswers.includes(2) ? 'False' : '—'}</span>
          </div>
        </div>
      )}

      {question.time_spent_seconds && (
        <div className="mt-3 text-xs text-slate-500">
          Time spent: {question.time_spent_seconds} seconds
        </div>
      )}
    </div>
  );
}
