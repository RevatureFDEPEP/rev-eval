'use client';

import { useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuthContext } from '@/lib/auth/AuthContext';
import { submitAnswer as defaultSubmitAnswer } from '@/lib/api/sessions';
import type { AnswerResult, SanitizedQuestion, SessionResponse } from '@/lib/api/types';
import { SingleSelectQuestion } from './SingleSelectQuestion';
import { MultiSelectQuestion } from './MultiSelectQuestion';

interface TestRunnerProps {
  session: SessionResponse;
  /** Injectable for tests so submit runs without the network. */
  submitAnswerFn?: (
    sessionId: string,
    submittedAnswers: (number | boolean)[],
    questionId?: string,
  ) => Promise<AnswerResult>;
}

/** Map the answer-Map's option_ids to the backend submit shape. TRUE_FALSE
 * renders synthesized options (1=True, 2=False) → convert to a bool. */
function toSubmittedAnswers(
  question: SanitizedQuestion,
  ids: number[],
): (number | boolean)[] {
  if (question.type?.toLowerCase() === 'true_false') {
    return ids.length > 0 ? [ids[0] === 1] : [];
  }
  return ids;
}

/**
 * Owns the interactive exam state (W3-F3 skeleton): the revealed `questions`,
 * `currentIndex`, and an `answers` Map keyed by question id. Sequential reveal —
 * the frontier (newest) question is the only editable one and carries Submit;
 * submitting it posts the answer and appends the server's `next_question`.
 * Previous/Next walk already-answered history read-only, mutating `currentIndex`
 * in React state with no App Router navigation, so selections are preserved.
 *
 * Plain useState + try/catch only. Timer, debounced autosave, submit-lock
 * reducer, and transient-retry are layered on in W3-F4.
 */
export function TestRunner({ session, submitAnswerFn = defaultSubmitAnswer }: TestRunnerProps) {
  // Read so the AuthProvider wiring is exercised; consumed by header UI later.
  useAuthContext();

  const seed = useMemo<SanitizedQuestion[]>(
    () => (session.question ? [session.question] : []),
    [session.question],
  );

  const [questions, setQuestions] = useState<SanitizedQuestion[]>(seed);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, number[]>>(
    () => new Map(Object.entries(session.draft_answers ?? {})),
  );
  const [status, setStatus] = useState<'ACTIVE' | 'SUBMITTED'>('ACTIVE');
  const [submittedAt, setSubmittedAt] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Guards against a double-submit racing two appends before state settles.
  const submittingRef = useRef(false);

  if (questions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm text-red-600">
        No questions available for this session.
      </div>
    );
  }

  const frontier = questions.length - 1;
  const isReviewing = currentIndex < frontier;
  const inputsDisabled = isReviewing || submitting || status === 'SUBMITTED';
  // Server index at mint (>0 on a resumed session) offsets the local list.
  const baseIndex = session.current_index;
  const isLastQuestion = baseIndex + frontier >= session.total_questions - 1;
  const question = questions[currentIndex];
  const selected = answers.get(question.id) ?? [];

  const setSelected = (ids: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(question.id, ids);
      return next;
    });
  };

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1));
  const goNext = () => setCurrentIndex((i) => Math.min(frontier, i + 1));

  const handleSubmit = async () => {
    if (submittingRef.current || status === 'SUBMITTED') return;
    const live = questions[frontier];
    submittingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitAnswerFn(
        session.session_id,
        toSubmittedAnswers(live, answers.get(live.id) ?? []),
        live.id,
      );
      if (result.status === 'SUBMITTED') {
        setStatus('SUBMITTED');
        setSubmittedAt(result.submitted_at ?? null);
      } else if (result.next_question) {
        const nq = result.next_question;
        setQuestions((prev) => (prev.some((x) => x.id === nq.id) ? prev : [...prev, nq]));
        setCurrentIndex((i) => i + 1);
      }
    } catch {
      setError('Could not submit your answer. Please try again.');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const renderQuestion = (q: SanitizedQuestion) =>
    q.type?.toLowerCase() === 'multi' ? (
      <MultiSelectQuestion
        question={q}
        selected={selected}
        onChange={setSelected}
        disabled={inputsDisabled}
      />
    ) : (
      <SingleSelectQuestion
        question={q}
        selected={selected}
        onChange={setSelected}
        disabled={inputsDisabled}
      />
    );

  if (status === 'SUBMITTED') {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6" data-testid="exam-confirmation">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Exam submitted</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Your answers are locked and have been recorded.
            {submittedAt ? ` Submitted at ${new Date(submittedAt).toLocaleString()}.` : ''}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <p className="text-sm text-muted-foreground">
        Question {baseIndex + currentIndex + 1} of {session.total_questions}
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="text-base leading-relaxed">{question.question_text}</CardTitle>
        </CardHeader>
        <CardContent>{renderQuestion(question)}</CardContent>
      </Card>

      {isReviewing && (
        <p className="text-xs text-muted-foreground">
          Reviewing an answered question — your selection is locked.
        </p>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={goPrev} disabled={currentIndex === 0 || submitting}>
          Previous
        </Button>
        {isReviewing ? (
          <Button onClick={goNext}>Next</Button>
        ) : (
          <Button onClick={handleSubmit} disabled={submitting || selected.length === 0}>
            {submitting ? 'Submitting…' : isLastQuestion ? 'Submit' : 'Submit & next'}
          </Button>
        )}
      </div>
    </div>
  );
}
