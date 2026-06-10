/**
 * TestRunner — the interactive test-taking shell (W3-F3 skeleton).
 *
 * Owns all client interactive state:
 *   - `currentIndex` (number): which question is on screen.
 *   - `answers` (`Map<string, number[]>`): selected option_ids keyed by question id.
 *
 * Navigation (Prev/Next) mutates `currentIndex` in React state ONLY — no App
 * Router navigation, no re-fetch — so selections in the answers Map survive
 * question switches.
 *
 * The W3-F1 backend is strictly sequential (one server-advanced question at a
 * time), so the live `questions` array is seeded with just the session's first
 * question. The full multi-question navigation machinery is built here as the
 * base layer; W3-F4 wires answer submission to append `next_question`.
 */
'use client';

import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useAuthContext } from '@/lib/auth/AuthContext';
import type { SanitizedQuestion, SessionOut } from '@/lib/api/types';
import { MultiSelectQuestion } from './MultiSelectQuestion';
import { SingleSelectQuestion } from './SingleSelectQuestion';

interface TestRunnerProps {
  session: SessionOut;
}

/** Polymorphic dispatch: render the right leaf component for the question type. */
function renderQuestion(
  question: SanitizedQuestion,
  selected: number[],
  onChange: (ids: number[]) => void,
) {
  switch (question.type) {
    case 'multi':
      return (
        <MultiSelectQuestion question={question} selected={selected} onChange={onChange} />
      );
    default:
      // mcq, true_false → single-select radio group.
      return (
        <SingleSelectQuestion question={question} selected={selected} onChange={onChange} />
      );
  }
}

export function TestRunner({ session }: TestRunnerProps) {
  const user = useAuthContext();

  // Seeded from the session's first (and currently only) sanitized question.
  const questions = useMemo<SanitizedQuestion[]>(
    () => (session.question ? [session.question] : []),
    [session.question],
  );

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, number[]>>(new Map());

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1));
  const goNext = () =>
    setCurrentIndex((i) => Math.min(questions.length - 1, i + 1));

  if (questions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm text-red-600">
        No questions available for this session.
      </div>
    );
  }

  const question = questions[currentIndex];
  const selected = answers.get(question.id) ?? [];

  const setSelected = (ids: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(question.id, ids);
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>
          Question {currentIndex + 1} of {session.total_questions}
        </span>
        <span data-testid="auth-identity">
          {user.email} ({user.role})
        </span>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg leading-relaxed">
            {question.question_text}
          </CardTitle>
        </CardHeader>
        <CardContent>{renderQuestion(question, selected, setSelected)}</CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={currentIndex === 0}
        >
          Previous
        </Button>
        <Button
          onClick={goNext}
          disabled={currentIndex >= questions.length - 1}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
