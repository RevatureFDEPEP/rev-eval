'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { getTestSessionBySubmission } from '@/lib/api';
import type { TestSubmission, TestSession, GradedQuizQuestion } from '@/lib/api/types';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { formatTableDate } from '@/lib/utils/date';

interface QuizSubmissionSheetProps {
  submission: TestSubmission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function QuizSubmissionSheet({
  submission,
  open,
  onOpenChange,
}: QuizSubmissionSheetProps) {
  const [session, setSession] = useState<TestSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!submission || !open) {
      setSession(null);
      setError(null);
      return;
    }

    const loadSession = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getTestSessionBySubmission(submission.id);
        setSession(data);
      } catch (err) {
        console.error('Failed to load quiz session:', err);
        setError(err instanceof Error ? err.message : 'Failed to load quiz details');
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, [submission, open]);

  if (!submission) return null;

  const renderQuestionCard = (question: GradedQuizQuestion, index: number) => {
    const isCorrect = question.is_correct;
    const hasOptions = question.options && question.options.length > 0;

    return (
      <Card key={`${question.question_id}-${index}`} className={`border ${isCorrect ? 'border-green-200 bg-green-50/30' : 'border-red-200 bg-red-50/30'}`}>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={isCorrect ? 'default' : 'destructive'} className="gap-1">
                  {isCorrect ? (
                    <>
                      <CheckCircle2 className="h-3 w-3" />
                      Correct
                    </>
                  ) : (
                    <>
                      <XCircle className="h-3 w-3" />
                      Incorrect
                    </>
                  )}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {question.difficulty}
                </Badge>
                <Badge variant="secondary" className="capitalize">
                  {question.question_type.replace('_', ' ')}
                </Badge>
              </div>
              <CardTitle className="text-base font-semibold text-slate-900">
                Question {index + 1}
              </CardTitle>
            </div>
            {question.time_spent_seconds && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Clock className="h-3 w-3" />
                {Math.round(question.time_spent_seconds)}s
              </div>
            )}
          </div>
          <CardDescription className="text-sm text-slate-700 whitespace-pre-wrap">
            {question.question_text}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {hasOptions ? (
            <div className="space-y-2">
              {question.options!.map((option) => {
                const isSelected = question.selected_answers?.includes(option.option_id);
                const isCorrectOption = question.correct_answers?.includes(option.option_id);

                let optionClass = 'rounded-lg border p-3 text-sm';
                if (isSelected && isCorrectOption) {
                  optionClass += ' border-green-500 bg-green-50 font-medium';
                } else if (isSelected && !isCorrectOption) {
                  optionClass += ' border-red-500 bg-red-50 font-medium';
                } else if (isCorrectOption) {
                  optionClass += ' border-green-300 bg-green-50/50';
                } else {
                  optionClass += ' border-slate-200 bg-slate-50';
                }

                return (
                  <div key={option.option_id} className={optionClass}>
                    <div className="flex items-start gap-2">
                      <span className="font-semibold text-slate-700">
                        {String.fromCharCode(65 + option.option_id - 1)}.
                      </span>
                      <span className="flex-1">{option.text}</span>
                      {isSelected && (
                        <Badge variant={isCorrectOption ? 'default' : 'destructive'} className="ml-2 text-xs">
                          {isCorrectOption ? 'Your answer ✓' : 'Your answer ✗'}
                        </Badge>
                      )}
                      {!isSelected && isCorrectOption && (
                        <Badge variant="outline" className="ml-2 text-xs border-green-500 text-green-700">
                          Correct answer
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-3">
              {question.selected_answers && question.selected_answers.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-medium text-slate-500 mb-2">Participant's Answer:</p>
                  <p className="text-sm text-slate-700">
                    {question.selected_answers[0] === 1 ? 'True' : 'False'}
                  </p>
                </div>
              )}
              {question.correct_answers && question.correct_answers.length > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                  <p className="text-xs font-medium text-green-700 mb-2">Correct Answer:</p>
                  <p className="text-sm text-green-900">
                    {question.correct_answers[0] === 1 ? 'True' : 'False'}
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[80vw]"
      >
        <SheetTitle className="sr-only">Quiz Submission #{submission.id}</SheetTitle>
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Submission #{submission.id}</Badge>
                <Badge variant="outline">Test ID: {submission.test_id}</Badge>
                <Badge>Status: {submission.status}</Badge>
                <Badge variant="default" className="bg-blue-600">Quiz</Badge>
              </div>
              <h2 className="text-3xl font-semibold text-slate-900">
                {submission.test?.name || 'Loading...'}
              </h2>
              <p className="max-w-2xl text-sm text-slate-500">
                View the participant's quiz submission with answers and scoring breakdown.
              </p>
            </div>
          </header>

          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </p>
              </CardContent>
            </Card>
          )}

          {loading ? (
            <div className="flex h-48 items-center justify-center text-sm text-slate-500">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading quiz details…
            </div>
          ) : session ? (
            <Tabs defaultValue="scores" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="scores">Scores & Summary</TabsTrigger>
                <TabsTrigger value="part-a">Part A Questions</TabsTrigger>
                <TabsTrigger value="part-b">Part B Questions</TabsTrigger>
              </TabsList>

              <TabsContent value="scores" className="space-y-4">
                <ScrollArea className="h-[calc(100vh-300px)]">
                  <div className="space-y-6 pr-4">
                    {/* Overall Score Card */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Overall Performance</CardTitle>
                        <CardDescription>Final quiz results and scoring breakdown</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                            <p className="text-xs uppercase tracking-wide text-purple-700">Total Score</p>
                            <p className="text-4xl font-bold text-purple-900">{session.total_score || 0}</p>
                            <p className="text-xs text-purple-600 mt-1">
                              out of {session.total_questions} questions
                            </p>
                          </div>
                          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                            <p className="text-xs uppercase tracking-wide text-blue-700">Percentage</p>
                            <p className="text-4xl font-bold text-blue-900">
                              {session.percentage_score ? Math.round(session.percentage_score) : 0}%
                            </p>
                            <p className="text-xs text-blue-600 mt-1">accuracy rate</p>
                          </div>
                        </div>

                        {/* Part A and Part B Scores */}
                        <div className="grid grid-cols-2 gap-4">
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm font-medium text-slate-700">Part A</p>
                              <Badge variant="outline">{session.part_a?.total_questions || 0} questions</Badge>
                            </div>
                            <p className="text-2xl font-bold text-slate-900">
                              {session.part_a?.score || 0}
                            </p>
                            {session.part_a?.total_questions && session.part_a?.score !== undefined && (
                              <p className="text-xs text-slate-600 mt-1">
                                {Math.round((session.part_a.score / session.part_a.total_questions) * 100)}% correct
                              </p>
                            )}
                          </div>
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm font-medium text-slate-700">Part B (Adaptive)</p>
                              <Badge variant="outline">{session.part_b?.total_questions || 0} questions</Badge>
                            </div>
                            <p className="text-2xl font-bold text-slate-900">
                              {session.part_b?.score || 0}
                            </p>
                            {session.part_b?.total_questions && session.part_b?.score !== undefined && (
                              <p className="text-xs text-slate-600 mt-1">
                                {Math.round((session.part_b.score / session.part_b.total_questions) * 100)}% correct
                              </p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Session Metadata */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Session Information</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Started At:</span>
                          <span className="text-slate-900">{formatTableDate(session.started_at)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Completed At:</span>
                          <span className="text-slate-900">
                            {session.completed_at ? formatTableDate(session.completed_at) : 'N/A'}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Status:</span>
                          <Badge variant="secondary">{session.status}</Badge>
                        </div>
                        {session.ai_model_used && (
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-500">AI Model Used:</span>
                            <span className="text-slate-900 font-mono text-xs">{session.ai_model_used}</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    {/* Participant Info */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Participant Details</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Name:</span>
                          <span className="text-slate-900">
                            {submission.participant_name || `User #${submission.user_id}`}
                          </span>
                        </div>
                        {submission.participant_email && (
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-500">Email:</span>
                            <span className="text-slate-900">{submission.participant_email}</span>
                          </div>
                        )}
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Submitted At:</span>
                          <span className="text-slate-900">
                            {submission.submitted_at ? formatTableDate(submission.submitted_at) : 'N/A'}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="part-a" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Part A Questions</CardTitle>
                    <CardDescription>
                      {session.part_a?.questions.length || 0} questions • Score: {session.part_a?.score || 0}/
                      {session.part_a?.total_questions || 0}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {!session.part_a || !session.part_a.questions || session.part_a.questions.length === 0 ? (
                      <div className="flex h-48 items-center justify-center text-muted-foreground">
                        <div className="text-center">
                          <p className="text-lg font-medium">No Part A Questions</p>
                          <p className="text-sm">Part A has not been completed yet.</p>
                        </div>
                      </div>
                    ) : (
                      <ScrollArea className="h-[calc(100vh-350px)]">
                        <div className="space-y-4 pr-4">
                          {session.part_a.questions.map((question, idx) => renderQuestionCard(question, idx))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="part-b" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Part B Questions (Adaptive)</CardTitle>
                    <CardDescription>
                      {session.part_b?.questions.length || 0} questions • Score: {session.part_b?.score || 0}/
                      {session.part_b?.total_questions || 0}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {!session.part_b || !session.part_b.questions || session.part_b.questions.length === 0 ? (
                      <div className="flex h-48 items-center justify-center text-muted-foreground">
                        <div className="text-center">
                          <p className="text-lg font-medium">No Part B Questions</p>
                          <p className="text-sm">Part B has not been completed yet.</p>
                        </div>
                      </div>
                    ) : (
                      <ScrollArea className="h-[calc(100vh-350px)]">
                        <div className="space-y-4 pr-4">
                          {session.part_b.questions.map((question, idx) => renderQuestionCard(question, idx))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
