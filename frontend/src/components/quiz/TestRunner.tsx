/**
 * TestRunner — client-side exam shell (W3-F3 skeleton + W3-F4 timer/autosave/submit-lock).
 *
 * Owns the interactive state: the buffered `questions`, the current index, and
 * the answers Map (question.id -> selected option_ids). The W3-F1/F2 backend is
 * strictly sequential — `POST /answer` scores the current question, advances,
 * and returns the next one — so "submit the exam" is the forward answer loop:
 * each submit appends the returned question to the buffer until the final one
 * flips session_status to SUBMITTED.
 *
 * W3-F4 layers on:
 *  - a server-anchored countdown (useServerTimer) that auto-submits at zero;
 *  - a 30s debounced draft autosave (useAutosave);
 *  - submit-and-lock via a useReducer state machine (examReducer): inputs/timer
 *    lock optimistically on submit, and only the server's ack confirms the result.
 *    A failed submit is recoverable — the primary button becomes "Try again".
 *  - draft rehydrate: the answers Map is seeded from session.draft_answers so a
 *    resumed session restores the current question's in-progress selection.
 *
 * Answered questions render read-only on backward review (forward-only model);
 * a resumed session can only continue forward (the contract returns one question
 * at a time, so prior questions aren't re-fetchable).
 */

'use client';

import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ParticipantQuestion, SessionResponse } from '@/lib/api/types';
import { SingleSelectQuestion } from './SingleSelectQuestion';
import { MultiSelectQuestion } from './MultiSelectQuestion';
import { Timer } from './Timer';
import { useServerTimer } from '@/lib/exam/useServerTimer';
import { useAutosave } from '@/lib/exam/useAutosave';
import { examReducer, initialExamState } from '@/lib/exam/examReducer';
import { submitAnswer } from '@/lib/api/sessions';
import { errorStatus } from '@/lib/exam/errors';

interface TestRunnerProps {
  session: SessionResponse;
  /** Test seam: seed multiple questions for navigation unit tests. Defaults to
   *  the single question the live W3-F1 contract returns. */
  initialQuestions?: ParticipantQuestion[];
}

/** Seed the answers Map from a resumed session's draft snapshot (W3-F4 rehydrate). */
function seedAnswers(draft: SessionResponse['draft_answers']): Map<string, number[]> {
  return new Map(Object.entries(draft ?? {}));
}

function submitErrorMessage(err: unknown): string {
  const status = errorStatus(err);
  if (status === 409 || status === 410) {
    return 'This quiz session has ended. Your earlier answers were saved.';
  }
  return 'We couldn’t submit your answer. Please try again or contact your trainer.';
}

export function TestRunner({ session, initialQuestions }: TestRunnerProps) {
  const [questions, setQuestions] = useState<ParticipantQuestion[]>(
    () => initialQuestions ?? [session.question]
  );
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, number[]>>(() =>
    seedAnswers(session.draft_answers)
  );
  const [exam, dispatch] = useReducer(examReducer, initialExamState);

  // Latest questions/answers via refs so handleSubmit stays referentially stable
  // (deps = [exam.status]) instead of being recreated on every selection — which
  // would otherwise churn the timer's onExpire ref every keystroke.
  const questionsRef = useRef(questions);
  const answersRef = useRef(answers);
  useEffect(() => {
    questionsRef.current = questions;
    answersRef.current = answers;
  });

  // One idempotency key per frontier question, stable across retries (manual
  // "Try again" or internal backoff) so a replayed submit returns the original
  // result instead of double-scoring; regenerated when the frontier advances.
  const idemRef = useRef<{ id: string; key: string } | null>(null);

  // Synchronous in-flight latch. The status guard below reads `exam.status` from
  // the render closure, which doesn't update until React commits — so two entries
  // in one batch (rapid double-click, or a timer onExpire coinciding with a click)
  // would both pass it and fire two submits / double-append the next question.
  // A ref set before the await closes that same-stack window; the status guard
  // still covers the cross-render cases.
  const inFlightRef = useRef(false);

  const setAnswer = useCallback((questionId: string, optionIds: number[]) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(questionId, optionIds);
      return next;
    });
  }, []);

  // Submit the frontier (current live, unanswered) question, append the next,
  // and advance. Optimistic lock via SUBMIT_START; the server ack confirms.
  // Re-runnable from the 'error' state (retry); blocked only mid-flight/finished.
  const handleSubmit = useCallback(async () => {
    if (inFlightRef.current) return;
    if (exam.status === 'submitting' || exam.status === 'submitted') return;
    inFlightRef.current = true;
    const qs = questionsRef.current;
    const frontier = qs[qs.length - 1];
    const selected = answersRef.current.get(frontier.id) ?? [];
    if (!idemRef.current || idemRef.current.id !== frontier.id) {
      idemRef.current = { id: frontier.id, key: crypto.randomUUID() };
    }
    dispatch({ type: 'SUBMIT_START' });
    try {
      const result = await submitAnswer(
        session.session_id,
        selected,
        frontier.id,
        idemRef.current.key
      );
      // Defensive: a non-final answer must return the next question. A null
      // question that isn't accompanied by a SUBMITTED status is a broken
      // contract that would otherwise soft-lock the shell (no Submit, a disabled
      // Next, no error) — and the timer's re-submit can't escape it. Surface it
      // as a recoverable error instead of stranding the participant.
      if (!result.question && result.session_status !== 'SUBMITTED') {
        dispatch({ type: 'SUBMIT_FAILED', error: submitErrorMessage(undefined) });
        return;
      }
      if (result.question) {
        const next = result.question;
        setQuestions((prev) => [...prev, next]);
        setCurrentIndex(qs.length); // new frontier index = old length
      }
      dispatch({ type: 'SUBMIT_CONFIRMED', result });
    } catch (err) {
      dispatch({ type: 'SUBMIT_FAILED', error: submitErrorMessage(err) });
    } finally {
      inFlightRef.current = false;
    }
  }, [exam.status, session.session_id]);

  const timer = useServerTimer(
    session.server_now,
    session.expires_at,
    handleSubmit, // onExpire auto-submits the frontier (best-effort expire-and-lock)
    exam.status === 'active' || exam.status === 'error'
  );
  const saveStatus = useAutosave(
    session.session_id,
    answers,
    exam.status === 'active'
  );

  const goPrev = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  const goNext = useCallback(() => {
    setCurrentIndex((i) => Math.min(questions.length - 1, i + 1));
  }, [questions.length]);

  const question = questions[currentIndex];
  const isFrontier = currentIndex === questions.length - 1;
  const isCurrentAnswered = exam.answeredIndices.has(question.index);

  // Lock states derived from status (no redundant stored flag):
  //  - inputs lock whenever not active (submitting/submitted/error) or when
  //    reviewing an already-answered question;
  //  - navigation locks only mid-flight/finished, so an error is still reviewable;
  //  - the primary button is disabled only while a submit is in flight.
  const inputsDisabled = exam.status !== 'active' || isCurrentAnswered;
  const navDisabled =
    exam.status === 'submitting' || exam.status === 'submitted';
  const submitting = exam.status === 'submitting';

  const renderQuestion = (q: ParticipantQuestion) => {
    const selected = answers.get(q.id) ?? [];
    switch (q.type) {
      case 'mcq':
        return (
          <SingleSelectQuestion
            question={q}
            selected={selected}
            onChange={(ids) => setAnswer(q.id, ids)}
            disabled={inputsDisabled}
          />
        );
      case 'multi':
        return (
          <MultiSelectQuestion
            question={q}
            selected={selected}
            onChange={(ids) => setAnswer(q.id, ids)}
            disabled={inputsDisabled}
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

  if (exam.status === 'submitted') {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <Card>
          <CardContent className="space-y-2 p-8 text-center">
            <h2 className="text-xl font-semibold text-slate-900">Quiz submitted</h2>
            <p className="text-sm text-slate-600">
              Your responses have been recorded. You can close this page.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        {/* Progress is keyed off the question's server-assigned index, not the
            local buffer position, so a resumed session counts correctly. */}
        <div className="text-sm text-slate-500">
          Question {question.index + 1} of {session.total_questions}
        </div>
        <div className="flex items-center gap-3">
          {saveStatus === 'saving' && (
            <span className="text-xs text-slate-400">Saving…</span>
          )}
          {saveStatus === 'saved' && (
            <span className="text-xs text-slate-400">Saved</span>
          )}
          <Timer
            timeRemaining={timer.timeRemaining}
            formatTime={timer.formatTime}
            isWarning={timer.isWarning}
            isCritical={timer.isCritical}
          />
        </div>
      </div>

      {exam.status === 'error' && exam.error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          {exam.error}
        </div>
      )}

      <Card>
        <CardContent className="space-y-6 p-6">
          <h2 className="text-lg font-medium leading-relaxed text-slate-900">
            {question.question_text}
          </h2>
          {renderQuestion(question)}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={currentIndex === 0 || navDisabled}
        >
          Previous
        </Button>

        {isFrontier && !isCurrentAnswered ? (
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting
              ? 'Submitting…'
              : exam.status === 'error'
                ? 'Try again'
                : 'Submit'}
          </Button>
        ) : (
          <Button onClick={goNext} disabled={isFrontier || navDisabled}>
            Next
          </Button>
        )}
      </div>
    </div>
  );
}
