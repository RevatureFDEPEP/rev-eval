/**
 * TestRunner — client-side quiz navigation shell (W3-F3).
 *
 * Owns all interactive state: the current question index and the answers Map
 * (question.id -> selected option_ids). Prev/Next mutate currentIndex in React
 * state only — no App Router navigation, no refetch — so selections survive
 * question switches.
 *
 * The W3-F1 backend is sequential and returns one question at a time, so the
 * live page seeds `questions` with the single current question. The full
 * multi-question machinery is built here; appending the next question on
 * answer-submit is W3-F4. (`initialQuestions` is a test seam for unit-testing
 * navigation against a multi-question fixture.)
 */

'use client';

import { useCallback, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ParticipantQuestion, SessionResponse } from '@/lib/api/types';
import { SingleSelectQuestion } from './SingleSelectQuestion';
import { MultiSelectQuestion } from './MultiSelectQuestion';

interface TestRunnerProps {
  session: SessionResponse;
  /** Test seam: seed multiple questions for navigation unit tests. Defaults to
   *  the single question the live W3-F1 contract returns. */
  initialQuestions?: ParticipantQuestion[];
}

export function TestRunner({ session, initialQuestions }: TestRunnerProps) {
  const [questions] = useState<ParticipantQuestion[]>(
    () => initialQuestions ?? [session.question]
  );
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, number[]>>(new Map());

  const setAnswer = useCallback((questionId: string, optionIds: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(questionId, optionIds);
      return next;
    });
  }, []);

  const goPrev = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  const goNext = useCallback(() => {
    setCurrentIndex((i) => Math.min(questions.length - 1, i + 1));
  }, [questions.length]);

  const renderQuestion = (q: ParticipantQuestion) => {
    const selected = answers.get(q.id) ?? [];
    switch (q.type) {
      case 'mcq':
        return (
          <SingleSelectQuestion
            question={q}
            selected={selected}
            onChange={(ids) => setAnswer(q.id, ids)}
          />
        );
      case 'multi':
        return (
          <MultiSelectQuestion
            question={q}
            selected={selected}
            onChange={(ids) => setAnswer(q.id, ids)}
          />
        );
      default:
        return (
          <div className="text-sm text-amber-600">
            Unsupported question type: {q.type}
          </div>
        );
    }
  };

  const question = questions[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === questions.length - 1;

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      {/* Progress is keyed off the question's server-assigned index, not the
          local buffer position. A resumed session returns the current question
          already advanced (e.g. current_index: 2), so buffer-relative counting
          would mislabel question 3 as "Question 1". */}
      <div className="text-sm text-slate-500">
        Question {question.index + 1} of {session.total_questions}
      </div>

      <Card>
        <CardContent className="space-y-6 p-6">
          <h2 className="text-lg font-medium leading-relaxed text-slate-900">
            {question.question_text}
          </h2>
          {renderQuestion(question)}
        </CardContent>
      </Card>

      {/* Local navigation appears once the buffer holds more than the single
          W3-F1 question (multi-question fixtures today; W3-F4 answer-submit
          will append the next question live). */}
      {questions.length > 1 && (
        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={goPrev} disabled={isFirst}>
            Previous
          </Button>
          <Button onClick={goNext} disabled={isLast}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
