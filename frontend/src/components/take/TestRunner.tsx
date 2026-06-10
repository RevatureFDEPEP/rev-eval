/**
 * TestRunner — the interactive test-taking shell.
 *
 * W3-F3 (skeleton) established: `currentIndex` + `answers` (`Map<string, number[]>`)
 * + polymorphic leaf rendering + React-state Prev/Next.
 *
 * W3-F4 layers the live exam behaviour on top:
 *   - a server-anchored countdown (`useServerTimer`) that auto-submits at zero;
 *   - debounced 30s autosave of in-progress answers (`useAutosave` → PATCH draft);
 *   - submit-and-lock via `useReducer` (`examReducer`): the primary action posts
 *     the current answer (`POST /sessions/{id}/answer`), appends the returned
 *     `next_question`, and advances; the final question finalizes the session
 *     (`status: SUBMITTED`) and renders a confirmation. Errors are classified
 *     transient (auto-retried in the client) vs semantic (surfaced + halted).
 *
 * Forward motion happens by SUBMITTING (the backend is strictly sequential and
 * grows the question list one answer at a time). `Previous`/`Next` navigate the
 * already-answered history read-only; the live (frontier) question is the only
 * editable one and carries the submit button.
 */
'use client';

import { useMemo, useReducer, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Timer } from '@/components/quiz/Timer';
import { useAuthContext } from '@/lib/auth/AuthContext';
import { submitAnswer as defaultSubmitAnswer, saveDraft as defaultSaveDraft } from '@/lib/api/sessions';
import { ExamError } from '@/lib/exam/errors';
import { examReducer, initialExamState } from '@/lib/exam/examReducer';
import { useAutosave } from '@/lib/exam/useAutosave';
import { useServerTimer } from '@/lib/exam/useServerTimer';
import type { AnswerResult, SanitizedQuestion, SessionOut } from '@/lib/api/types';
import { MultiSelectQuestion } from './MultiSelectQuestion';
import { SingleSelectQuestion } from './SingleSelectQuestion';

interface TestRunnerProps {
  session: SessionOut;
  /** Seed override (multi-question tests); defaults to the session's first question. */
  initialQuestions?: SanitizedQuestion[];
  /** Injectable for tests so submit/autosave run without the network. */
  submitAnswerFn?: (
    sessionId: string,
    submittedAnswers: number[],
  ) => Promise<AnswerResult>;
  saveDraftFn?: (
    sessionId: string,
    answers: Record<string, number[]>,
  ) => Promise<unknown>;
}

/** Polymorphic dispatch: render the right leaf component for the question type. */
function renderQuestion(
  question: SanitizedQuestion,
  selected: number[],
  onChange: (ids: number[]) => void,
  disabled: boolean,
) {
  switch (question.type) {
    case 'multi':
      return (
        <MultiSelectQuestion
          question={question}
          selected={selected}
          onChange={onChange}
          disabled={disabled}
        />
      );
    default:
      // mcq, true_false → single-select radio group.
      return (
        <SingleSelectQuestion
          question={question}
          selected={selected}
          onChange={onChange}
          disabled={disabled}
        />
      );
  }
}

export function TestRunner({
  session,
  initialQuestions,
  submitAnswerFn = defaultSubmitAnswer,
  saveDraftFn = defaultSaveDraft,
}: TestRunnerProps) {
  const user = useAuthContext();

  const seed = useMemo<SanitizedQuestion[]>(
    () => initialQuestions ?? (session.question ? [session.question] : []),
    [initialQuestions, session.question],
  );

  const [questions, setQuestions] = useState<SanitizedQuestion[]>(seed);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, number[]>>(new Map());
  const [exam, dispatch] = useReducer(examReducer, initialExamState);
  const submittingRef = useRef(false);

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1));
  const goNext = () =>
    setCurrentIndex((i) => Math.min(questions.length - 1, i + 1));

  const handleSubmit = async () => {
    if (submittingRef.current || exam.isLocked) return;
    if (questions.length === 0) return;
    const q = questions[questions.length - 1]; // the live (frontier) question
    submittingRef.current = true;
    dispatch({ type: 'SUBMIT_START' });
    try {
      const result = await submitAnswerFn(
        session.session_id,
        answers.get(q.id) ?? [],
      );
      if (result.status === 'SUBMITTED') {
        dispatch({
          type: 'SUBMIT_CONFIRMED',
          finalized: true,
          submittedAt: result.submitted_at,
        });
      } else {
        if (result.next_question) {
          const nq = result.next_question;
          setQuestions((prev) =>
            prev.some((x) => x.id === nq.id) ? prev : [...prev, nq],
          );
          setCurrentIndex((i) => i + 1);
        }
        dispatch({ type: 'SUBMIT_CONFIRMED', finalized: false });
      }
    } catch (err) {
      const kind = err instanceof ExamError ? err.kind : 'semantic';
      const message = err instanceof Error ? err.message : 'Submission failed';
      dispatch({ type: 'SUBMIT_FAILED', kind, message });
    } finally {
      submittingRef.current = false;
    }
  };

  // Server-anchored countdown; stops once the exam is no longer active.
  const timer = useServerTimer(
    session.server_now,
    session.expires_at,
    handleSubmit,
    exam.status === 'active',
  );

  // Debounced 30s autosave of in-progress answers while the exam is active.
  const saveStatus = useAutosave(
    session.session_id,
    answers,
    exam.status === 'active',
    undefined,
    saveDraftFn,
  );

  if (questions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm text-red-600">
        No questions available for this session.
      </div>
    );
  }

  const frontier = questions.length - 1;
  const isReviewing = currentIndex < frontier;
  const inputsDisabled = exam.isLocked || isReviewing;
  const isLastQuestion = frontier >= session.total_questions - 1;

  const question = questions[currentIndex];
  const selected = answers.get(question.id) ?? [];

  const setSelected = (ids: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(question.id, ids);
      return next;
    });
  };

  if (exam.status === 'submitted') {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6" data-testid="exam-confirmation">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Exam submitted</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            Your answers are locked and have been recorded. You may now close this
            window.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm text-slate-500">
          Question {currentIndex + 1} of {session.total_questions}
        </span>
        <div className="w-40">
          <Timer
            timeRemaining={timer.timeRemaining}
            formatTime={timer.formatTime}
            isWarning={timer.isWarning}
            isCritical={timer.isCritical}
          />
        </div>
        <span data-testid="auth-identity" className="text-sm text-slate-500">
          {user.email} ({user.role})
        </span>
      </div>

      {exam.status === 'error' && exam.error && (
        <div
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700"
        >
          {exam.error.kind === 'transient'
            ? 'Network problem submitting your answer. Please check your connection.'
            : 'Your submission was rejected by the server.'}{' '}
          {exam.error.message}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg leading-relaxed">
            {question.question_text}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {renderQuestion(question, selected, setSelected, inputsDisabled)}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={currentIndex === 0 || exam.status === 'submitting'}
        >
          Previous
        </Button>

        {isReviewing ? (
          <Button onClick={goNext}>Next</Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={exam.status === 'submitting'}
            data-testid="submit-button"
          >
            {exam.status === 'submitting'
              ? 'Submitting…'
              : isLastQuestion
                ? 'Submit Exam'
                : 'Submit Answer'}
          </Button>
        )}
      </div>

      <div className="text-right text-xs text-slate-400" data-testid="save-status">
        {saveStatus === 'saving' && 'Saving…'}
        {saveStatus === 'saved' && 'Draft saved'}
        {saveStatus === 'error' && 'Autosave failed'}
      </div>
    </div>
  );
}
