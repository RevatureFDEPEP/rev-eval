'use client';

import { useMemo, useReducer, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Timer } from '@/components/quiz/Timer';
import { useAuthContext } from '@/lib/auth/AuthContext';
import {
  submitAnswer as defaultSubmitAnswer,
  saveDraft as defaultSaveDraft,
  newIdempotencyKey,
} from '@/lib/api/sessions';
import { ExamError } from '@/lib/exam/errors';
import { examReducer, initialExamState } from '@/lib/exam/examReducer';
import { useAutosave } from '@/lib/exam/useAutosave';
import { useServerTimer } from '@/lib/exam/useServerTimer';
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
    idempotencyKey?: string,
  ) => Promise<AnswerResult>;
  /** Injectable for tests so autosave runs without the network. */
  saveDraftFn?: (
    sessionId: string,
    answers: Record<string, number[]>,
  ) => Promise<unknown>;
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
 * Owns the interactive exam state. W3-F3 established the sequential-reveal
 * skeleton (`questions`, `currentIndex`, `answers` Map keyed by question id;
 * the frontier question is the only editable one and carries Submit).
 *
 * W3-F4 layers the live exam behaviour on top:
 *   - `useServerTimer` — server-anchored countdown that AUTO-SUBMITS the
 *     frontier answer at zero (onExpire = handleSubmit; single-fire);
 *   - `useAutosave` — debounced 30s `PATCH /sessions/{id}/draft` of the full
 *     in-progress answer map, so a crash/close doesn't cost progress;
 *   - `examReducer` (`useReducer`) — submit-and-lock: SUBMIT_START locks inputs
 *     + timer optimistically (before the server responds) and only a confirmed
 *     non-final answer unlocks; failures stay locked, classified transient
 *     (offer Retry, same idempotency key) vs semantic (surface + halt).
 */
export function TestRunner({
  session,
  submitAnswerFn = defaultSubmitAnswer,
  saveDraftFn = defaultSaveDraft,
}: TestRunnerProps) {
  const user = useAuthContext();

  const seed = useMemo<SanitizedQuestion[]>(
    () => (session.question ? [session.question] : []),
    [session.question],
  );

  const [questions, setQuestions] = useState<SanitizedQuestion[]>(seed);
  const [currentIndex, setCurrentIndex] = useState(0);
  // Resumed sessions restore the autosaved draft selections.
  const [answers, setAnswers] = useState<Map<string, number[]>>(
    () => new Map(Object.entries(session.draft_answers ?? {})),
  );
  const [exam, dispatch] = useReducer(examReducer, initialExamState);
  // Guards against a double-submit racing two appends before state settles.
  const submittingRef = useRef(false);
  // Stable idempotency key for the in-flight logical submit; reused across this
  // submission's retries (handleRetry) so a transient blip replays, not rescores.
  const submitKeyRef = useRef<string | null>(null);

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1));
  const goNext = () => setCurrentIndex((i) => Math.min(questions.length - 1, i + 1));

  // Shared submit body — entered via handleSubmit (fresh key) or handleRetry
  // (reused key); the caller dispatches its own entry action + sets the key.
  const performSubmit = async () => {
    if (questions.length === 0) return;
    const live = questions[questions.length - 1]; // the live (frontier) question
    submittingRef.current = true;
    try {
      const result = await submitAnswerFn(
        session.session_id,
        toSubmittedAnswers(live, answers.get(live.id) ?? []),
        live.id,
        submitKeyRef.current ?? undefined,
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
          setQuestions((prev) => (prev.some((x) => x.id === nq.id) ? prev : [...prev, nq]));
          setCurrentIndex((i) => i + 1);
        }
        dispatch({ type: 'SUBMIT_CONFIRMED', finalized: false });
        submitKeyRef.current = null; // logical submit complete
      }
    } catch (err) {
      const kind = err instanceof ExamError ? err.kind : 'semantic';
      const message = err instanceof Error ? err.message : 'Submission failed';
      dispatch({ type: 'SUBMIT_FAILED', kind, message });
    } finally {
      submittingRef.current = false;
    }
  };

  const handleSubmit = async () => {
    if (submittingRef.current || exam.isLocked) return;
    submitKeyRef.current = newIdempotencyKey(); // fresh key for a new submission
    dispatch({ type: 'SUBMIT_START' });
    await performSubmit();
  };

  // Recovery from a transient-exhausted submit: re-enter `submitting` (still
  // locked) and re-send with the SAME idempotency key. Semantic errors never
  // get here — the reducer ignores SUBMIT_RETRY for them and no button renders.
  const handleRetry = async () => {
    if (submittingRef.current) return;
    if (exam.status !== 'error' || exam.error?.kind !== 'transient') return;
    dispatch({ type: 'SUBMIT_RETRY' });
    await performSubmit();
  };

  // Server-anchored countdown; auto-submits the frontier answer at zero and
  // stops ticking once the exam is no longer active (submit/lock cycles).
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

  if (exam.status === 'submitted') {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6" data-testid="exam-confirmation">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Exam submitted</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Your answers are locked and have been recorded.
            {exam.submittedAt
              ? ` Submitted at ${new Date(exam.submittedAt).toLocaleString()}.`
              : ''}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm text-muted-foreground">
          Question {baseIndex + currentIndex + 1} of {session.total_questions}
        </span>
        <div className="w-40">
          <Timer
            timeRemaining={timer.timeRemaining}
            formatTime={timer.formatTime}
            isWarning={timer.isWarning}
            isCritical={timer.isCritical}
          />
        </div>
        <span data-testid="auth-identity" className="text-sm text-muted-foreground">
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
          {exam.error.kind === 'transient' && (
            <Button
              variant="outline"
              size="sm"
              className="ml-3"
              onClick={handleRetry}
              data-testid="retry-button"
            >
              Retry submission
            </Button>
          )}
        </div>
      )}

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
            disabled={exam.status === 'submitting' || selected.length === 0}
            data-testid="submit-button"
          >
            {exam.status === 'submitting'
              ? 'Submitting…'
              : isLastQuestion
                ? 'Submit'
                : 'Submit & next'}
          </Button>
        )}
      </div>

      <div className="text-right text-xs text-muted-foreground" data-testid="save-status">
        {saveStatus === 'saving' && 'Saving…'}
        {saveStatus === 'saved' && 'Draft saved'}
        {saveStatus === 'error' && 'Autosave failed'}
      </div>
    </div>
  );
}
