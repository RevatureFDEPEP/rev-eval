'use client';

import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { QuestionCard } from '@/components/quiz/QuestionCard';
import { useAuthContext } from '@/lib/auth/AuthContext';
import type { QuizQuestion, QuizSessionRead } from '@/lib/api/types';
import { cn } from '@/lib/utils';

type QuestionResponse = number | number[] | boolean;

interface TestRunnerProps {
  session: Omit<QuizSessionRead, 'session_token'>;
}

function selectedResponse(question: QuizQuestion, values: number[]): QuestionResponse | null {
  if (question.question_type === 'multi') return values;
  if (question.question_type === 'true_false') {
    if (values[0] === 1) return true;
    if (values[0] === 0) return false;
    return null;
  }
  return values[0] ?? null;
}

function responseToValues(response: QuestionResponse): number[] {
  if (Array.isArray(response)) return response;
  if (typeof response === 'boolean') return [response ? 1 : 0];
  return [response];
}

function initialQuestions(session: Omit<QuizSessionRead, 'session_token'>): QuizQuestion[] {
  if (session.questions.length > 0) return session.questions;
  return session.first_question ? [session.first_question] : [];
}

export function TestRunner({ session }: TestRunnerProps) {
  const identity = useAuthContext();
  const questions = useMemo(() => initialQuestions(session), [session]);
  const initialIndex =
    questions.length > 0
      ? Math.min(Math.max(session.current_index, 0), questions.length - 1)
      : 0;
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [answers, setAnswers] = useState<Map<string, number[]>>(() => new Map());

  const currentQuestion = questions[currentIndex] ?? questions[0] ?? null;
  const answeredQuestionIds = useMemo(() => new Set(answers.keys()), [answers]);
  const answeredCount = answeredQuestionIds.size;
  const progress =
    questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0;

  const handleAnswerChange = (questionId: string, response: QuestionResponse) => {
    setAnswers((previous) => {
      const next = new Map(previous);
      const values = responseToValues(response);
      if (values.length === 0) {
        next.delete(questionId);
      } else {
        next.set(questionId, values);
      }
      return next;
    });
  };

  const goPrevious = () => setCurrentIndex((index) => Math.max(0, index - 1));
  const goNext = () =>
    setCurrentIndex((index) => Math.min(questions.length - 1, index + 1));
  const goToQuestion = (index: number) => setCurrentIndex(index);

  if (questions.length === 0 || currentQuestion === null) {
    return (
      <Card className="mx-auto max-w-xl border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-lg text-amber-950">No questions available</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-amber-900">
          This test session did not return any quiz questions.
        </CardContent>
      </Card>
    );
  }

  const selected = selectedResponse(
    currentQuestion,
    answers.get(currentQuestion.question_id) ?? [],
  );

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <section className="space-y-4 border-b border-slate-200 pb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                Quiz
              </Badge>
              <Badge variant="outline" className="rounded-full px-3 py-1">
                {session.status.replaceAll('_', ' ')}
              </Badge>
            </div>
            <h1 className="text-2xl font-semibold text-slate-950 sm:text-3xl">
              Test #{session.test_id}
            </h1>
            <p className="text-sm text-slate-600">
              {identity.email} · Question {currentIndex + 1} of {questions.length}
            </p>
          </div>
          <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm">
            <span className="font-medium text-slate-950">{answeredCount}</span> /{' '}
            {questions.length} answered
          </div>
        </div>
        <Progress value={progress} className="h-2" />
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <main className="space-y-5">
          <QuestionCard
            question={currentQuestion}
            questionNumber={currentIndex + 1}
            selectedAnswer={selected}
            onAnswerChange={(response) =>
              handleAnswerChange(currentQuestion.question_id, response)
            }
          />

          <div className="flex items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={goPrevious}
              disabled={currentIndex === 0}
              className="gap-2"
            >
              <ChevronLeft className="size-4" />
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={goNext}
              disabled={currentIndex === questions.length - 1}
              className="gap-2"
            >
              Next
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </main>

        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Questions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-2">
                {questions.map((question, index) => {
                  const isCurrent = index === currentIndex;
                  const isAnswered = answeredQuestionIds.has(question.question_id);
                  return (
                    <Button
                      key={question.question_id}
                      type="button"
                      variant="outline"
                      size="icon"
                      aria-current={isCurrent ? 'page' : undefined}
                      aria-label={`Go to question ${index + 1}`}
                      onClick={() => goToQuestion(index)}
                      className={cn(
                        'h-10 w-10 rounded-md border text-sm',
                        isCurrent &&
                          'border-blue-600 bg-blue-600 text-white hover:bg-blue-600',
                        !isCurrent &&
                          isAnswered &&
                          'border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
                      )}
                    >
                      {index + 1}
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
