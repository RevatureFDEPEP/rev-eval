'use client';

import { useState, useCallback } from 'react';
import { TmsSessionStartResponse, TmsQuestion, TmsQuestionType } from '@/lib/api/types';
import { SingleSelectQuestion } from './SingleSelectQuestion';
import { MultiSelectQuestion } from './MultiSelectQuestion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// session_token is a server-minted bearer secret and must never reach the
// client bundle — the server component drops it before passing the session.
export type ClientSession = Omit<TmsSessionStartResponse, 'session_token'>;

interface TestRunnerProps {
  session: ClientSession;
}

export function TestRunner({ session }: TestRunnerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  // answers: question._id → selected option IDs
  const [answers, setAnswers] = useState<Map<string, number[]>>(new Map());

  const questions = session.questions;
  const currentQuestion: TmsQuestion | undefined = questions[currentIndex];
  const totalQuestions = questions.length;

  const setAnswer = useCallback((questionId: string, optionIds: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(questionId, optionIds);
      return next;
    });
  }, []);

  function renderQuestion(question: TmsQuestion) {
    const type: TmsQuestionType = question.type;
    const currentAnswer = answers.get(question._id) ?? [];

    switch (type) {
      case 'mcq':
        return (
          <SingleSelectQuestion
            question={question}
            selectedAnswer={currentAnswer[0] ?? null}
            onAnswerChange={(optionId) => setAnswer(question._id, [optionId])}
          />
        );
      case 'multi':
        return (
          <MultiSelectQuestion
            question={question}
            selectedAnswers={currentAnswer}
            onAnswerChange={(optionIds) => setAnswer(question._id, optionIds)}
          />
        );
      default:
        return (
          <p className="text-sm text-slate-500">
            Question type &ldquo;{type}&rdquo; is not supported in this view.
          </p>
        );
    }
  }

  const answeredCount = answers.size;
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex < totalQuestions - 1;
  const progressPercent = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b bg-white shadow-sm">
        <div className="container mx-auto flex items-center justify-between px-4 py-3">
          <div>
            <p className="text-xs text-slate-500">
              Question {currentIndex + 1} of {totalQuestions}
            </p>
            <p className="text-xs text-slate-400">
              {answeredCount} answered
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentIndex((i) => i - 1)}
              disabled={!hasPrevious}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentIndex((i) => i + 1)}
              disabled={!hasNext}
            >
              Next
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto max-w-3xl px-4 py-8">
        {/* Progress bar */}
        <div className="mb-6 h-1.5 w-full rounded-full bg-slate-200">
          <div
            className="h-1.5 rounded-full bg-blue-600 transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Question card */}
        {currentQuestion ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-medium leading-relaxed text-slate-900">
                {currentQuestion.question_text}
              </CardTitle>
            </CardHeader>
            <CardContent>{renderQuestion(currentQuestion)}</CardContent>
          </Card>
        ) : (
          <p className="text-center text-slate-500">No questions available.</p>
        )}

        {/* Navigation footer */}
        <div className="mt-6 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setCurrentIndex((i) => i - 1)}
            disabled={!hasPrevious}
          >
            ← Previous
          </Button>

          {/* Question dot navigator */}
          <div className="flex flex-wrap justify-center gap-1.5">
            {questions.map((q, idx) => (
              <button
                key={q._id}
                onClick={() => setCurrentIndex(idx)}
                className={`size-2.5 rounded-full transition-colors ${
                  idx === currentIndex
                    ? 'bg-blue-600'
                    : answers.has(q._id)
                      ? 'bg-green-500'
                      : 'bg-slate-300'
                }`}
                aria-label={`Go to question ${idx + 1}`}
              />
            ))}
          </div>

          <Button
            variant="outline"
            onClick={() => setCurrentIndex((i) => i + 1)}
            disabled={!hasNext}
          >
            Next →
          </Button>
        </div>
      </div>
    </div>
  );
}
