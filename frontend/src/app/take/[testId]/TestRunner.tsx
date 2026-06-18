'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { QuestionCard } from '@/components/quiz/QuestionCard';
import { AuthProvider, type AuthUser } from '@/context/AuthContext';
import { submitAnswer, type SessionRead } from '@/lib/api/sessions';
import type { QuizQuestion } from '@/lib/api/types';

type AnswerValue = number | number[] | boolean;

function answerToSubmitted(value: AnswerValue | undefined): (number | boolean | string)[] {
  if (value === undefined) return [];
  if (Array.isArray(value)) return value;
  return [value as number | boolean];
}

interface TestRunnerProps {
  quizSession: SessionRead;
  user: AuthUser;
}

export default function TestRunner({ quizSession, user }: TestRunnerProps) {
  const router = useRouter();

  const initialQuestions: QuizQuestion[] = quizSession.first_question
    ? [quizSession.first_question]
    : [];

  const [questions, setQuestions] = useState<QuizQuestion[]>(initialQuestions);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, AnswerValue>>(new Map());
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);

  const currentQuestion = questions[currentIndex] ?? null;
  const isFirst = currentIndex === 0;
  // Whether we already have the next question in the local cache.
  const hasNextCached = currentIndex < questions.length - 1;

  const handleAnswerChange = useCallback(
    (answer: AnswerValue) => {
      if (!currentQuestion) return;
      setAnswers((prev) => {
        const next = new Map(prev);
        next.set(currentQuestion.question_id, answer);
        return next;
      });
    },
    [currentQuestion],
  );

  const handlePrevious = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  // "Next" navigates to the cached next question or fetches it via answer submission.
  const handleNext = useCallback(async () => {
    if (!currentQuestion) return;

    if (hasNextCached) {
      setCurrentIndex((i) => i + 1);
      return;
    }

    setFetching(true);
    setFetchError(null);
    try {
      const submitted = answerToSubmitted(answers.get(currentQuestion.question_id));
      const resp = await submitAnswer(
        quizSession.session_id,
        currentQuestion.question_id,
        submitted,
      );

      if (resp.session_status === 'SUBMITTED') {
        setCompleted(true);
        return;
      }

      if (resp.next_question) {
        setQuestions((prev) => [...prev, resp.next_question!]);
        setCurrentIndex((i) => i + 1);
      }
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load next question');
    } finally {
      setFetching(false);
    }
  }, [currentQuestion, hasNextCached, answers, quizSession.session_id]);

  if (completed) {
    return (
      <AuthProvider user={user}>
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <Card className="w-full max-w-md border-green-200">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-4">
                <CheckCircle2 className="size-12 text-green-600" />
                <div className="text-center">
                  <h2 className="text-lg font-semibold text-slate-900">Quiz Submitted!</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Your answers have been recorded.
                  </p>
                </div>
                <Button onClick={() => router.push('/participant/tests')}>
                  Back to Tests
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </AuthProvider>
    );
  }

  if (!currentQuestion) {
    return (
      <AuthProvider user={user}>
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <Card className="w-full max-w-md border-red-200">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-4">
                <AlertCircle className="size-12 text-red-600" />
                <p className="text-center text-sm text-slate-600">
                  No questions available for this test.
                </p>
                <Button variant="outline" onClick={() => router.push('/participant/tests')}>
                  Back to Tests
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </AuthProvider>
    );
  }

  const answeredCount = answers.size;

  return (
    <AuthProvider user={user}>
      <div className="min-h-screen bg-slate-50 pb-8">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="container mx-auto flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500">Test #{quizSession.test_id}</p>
              <p className="text-sm font-medium text-slate-800">
                Question {currentIndex + 1}{' '}
                <span className="text-slate-400">of {questions.length}</span>
              </p>
            </div>
            <p className="text-xs text-slate-500">{answeredCount} answered</p>
          </div>
        </div>

        <div className="container mx-auto mt-6 max-w-2xl px-4">
          {/* Error banner */}
          {fetchError && (
            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {fetchError}
            </div>
          )}

          {/* Question */}
          <QuestionCard
            question={currentQuestion}
            questionNumber={currentIndex + 1}
            selectedAnswer={answers.get(currentQuestion.question_id) ?? null}
            onAnswerChange={handleAnswerChange}
          />

          {/* Navigation */}
          <div className="mt-6 flex items-center justify-between gap-4">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={isFirst || fetching}
            >
              <ChevronLeft className="mr-1 size-4" />
              Previous
            </Button>

            <Button onClick={handleNext} disabled={fetching}>
              {fetching ? 'Loading…' : 'Next'}
              <ChevronRight className="ml-1 size-4" />
            </Button>
          </div>
        </div>
      </div>
    </AuthProvider>
  );
}
