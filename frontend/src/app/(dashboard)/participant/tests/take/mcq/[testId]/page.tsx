'use client';

import { useEffect, useState, useCallback, use, useMemo, useRef, useReducer } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import {
  getTest,
  createTestSession,
  getPartAQuestions,
  submitPartA,
  getPartBQuestions,
  submitPartB,
  getCurrentUser,
  ApiError,
} from '@/lib/api';
import { Test, QuizQuestion, QuizAnswer } from '@/lib/api/types';
import { useTimer } from '@/lib/hooks/useTimer';
import { useAutosave } from '@/lib/hooks/useAutosave';
import {
  submitReducer,
  SUBMIT_INITIAL_STATE,
  canSubmit,
  isTerminalError,
} from '@/lib/submitMachine';
import { Timer } from '@/components/quiz/Timer';
import { ProgressHeader } from '@/components/quiz/ProgressHeader';
import { QuestionCard } from '@/components/quiz/QuestionCard';
import { QuestionNavigation } from '@/components/quiz/QuestionNavigation';
import { PartTransition } from '@/components/quiz/PartTransition';

interface QuizTestPageProps {
  params: Promise<{
    testId: string;
  }>;
}

type Part = 'A' | 'B';
type QuizState = 'loading' | 'part-a' | 'transitioning' | 'part-b' | 'submitting' | 'completed' | 'error';

type AnswerValue = number | number[] | boolean;

export default function QuizTestPage({ params }: QuizTestPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const resolvedParams = use(params);

  const testId = parseInt(resolvedParams.testId, 10);
  const submissionId = parseInt(searchParams.get('submission') || '', 10);

  // ─── ALL HOOKS MUST BE DECLARED BEFORE ANY CONDITIONAL RETURN ───────────────

  const [state, setState] = useState<QuizState>('loading');
  const [test, setTest] = useState<Test | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPart, setCurrentPart] = useState<Part>('A');
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [partAQuestions, setPartAQuestions] = useState<QuizQuestion[]>([]);
  const [partBQuestions, setPartBQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [answers, setAnswers] = useState<Map<string, AnswerValue>>(new Map());
  const [submittedPartAQuestionIds, setSubmittedPartAQuestionIds] = useState<Set<string>>(
    () => new Set()
  );
  const [error, setError] = useState<string | null>(null);

  // 6-state submit machine — tracks submit button lifecycle independently of page state
  const [submitState, dispatchSubmit] = useReducer(submitReducer, SUBMIT_INITIAL_STATE);

  const answeredQuestionIds = useMemo(() => {
    const combined = new Set<string>();
    submittedPartAQuestionIds.forEach((id) => combined.add(id));
    answers.forEach((_, questionId) => combined.add(questionId));
    return combined;
  }, [submittedPartAQuestionIds, answers]);

  const answeredCount = answeredQuestionIds.size;

  const currentPartAnsweredCount = useMemo(() => {
    return questions.reduce((count, question) => {
      return answeredQuestionIds.has(question.question_id) ? count + 1 : count;
    }, 0);
  }, [questions, answeredQuestionIds]);

  // Warn user if they try to leave during an active test
  useEffect(() => {
    const shouldWarn = state !== 'completed' && state !== 'error' && state !== 'loading';
    if (!shouldWarn) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue =
        'You are leaving the test. Your progress may be lost and the test may be marked as abandoned. Are you sure you want to leave?';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [state]);

  // Ref breaks circular dep: useTimer needs onTimeExpired, handlers need timer.pause/resume
  const handleTimeExpiredRef = useRef<() => Promise<void>>(async () => {});

  const derivedTotalQuestions =
    typeof test?.number_of_questions === 'number' && test.number_of_questions > 0
      ? test.number_of_questions
      : undefined;

  const expectedPartBCount = useMemo(() => {
    const totalRemaining =
      derivedTotalQuestions != null
        ? Math.max(derivedTotalQuestions - partAQuestions.length, 0)
        : 0;
    return Math.max(totalRemaining, partBQuestions.length);
  }, [derivedTotalQuestions, partAQuestions.length, partBQuestions.length]);

  const partBQuestionsForNavigation = useMemo(() => {
    if (partBQuestions.length > 0) {
      return partBQuestions;
    }
    if (expectedPartBCount <= 0) {
      return [] as QuizQuestion[];
    }
    return Array.from({ length: expectedPartBCount }, (_, index) => ({
      question_id: `placeholder-B-${index}`,
      question_text: `Part B Question ${index + 1}`,
      question_type: 'mcq' as const,
      difficulty: 'easy',
      options: [],
    } as QuizQuestion));
  }, [partBQuestions, expectedPartBCount]);

  const totalDuration = test?.duration_seconds ?? 0;

  const timer = useTimer({
    durationSeconds: totalDuration || 0,
    testId: isNaN(testId) ? '0' : testId.toString(),
    onTimeExpired: () => handleTimeExpiredRef.current(),
    autoStart: false,
  });

  const pauseTimer = timer.pause;
  const resumeTimer = timer.resume;
  const resetTimer = timer.reset;

  // Debounced autosave — persists draft answers to localStorage with idempotency keys
  useAutosave({ sessionId, answers });

  useEffect(() => {
    if (state === 'part-a' || state === 'part-b') {
      resumeTimer();
    } else {
      pauseTimer();
    }
  }, [state, pauseTimer, resumeTimer]);

  // Submit Part A handler
  const handleSubmitPartA = useCallback(async () => {
    if (!sessionId || !canSubmit(submitState)) return;

    try {
      setState('transitioning');
      pauseTimer();
      dispatchSubmit({ type: 'SUBMIT' });

      const answersArray: QuizAnswer[] = Array.from(answers.entries()).map(([qId, answer]) => ({
        question_id: qId,
        selected_answers: Array.isArray(answer)
          ? answer
          : typeof answer === 'boolean'
            ? [answer ? 1 : 0]
            : [answer],
      }));

      await submitPartA({
        session_id: sessionId,
        answers: answersArray,
      });

      dispatchSubmit({ type: 'SUCCESS' });

      const partBData = await getPartBQuestions(sessionId);
      setPartBQuestions(partBData.questions);
      setQuestions(partBData.questions);
      setCurrentPart('B');
      setCurrentQuestionIndex(0);
      setSubmittedPartAQuestionIds(
        new Set(partAQuestions.map((question) => question.question_id))
      );
      setAnswers(new Map());
      dispatchSubmit({ type: 'RESET' }); // reset machine for Part B submit

      localStorage.setItem(`quiz-part-${testId}`, 'B');
      localStorage.removeItem(`quiz-answers-${testId}`);
      localStorage.removeItem(`quiz-draft-${sessionId}`);

      setState('part-b');
      resumeTimer();
      toast.success('Part A submitted! Starting Part B...');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          // Already submitted — treat as success and move to Part B
          dispatchSubmit({ type: 'ERROR_TERMINAL_409', message: 'Part A already submitted.' });
          toast.info('Part A was already submitted. Loading Part B...');
          try {
            const partBData = await getPartBQuestions(sessionId);
            setPartBQuestions(partBData.questions);
            setQuestions(partBData.questions);
            setCurrentPart('B');
            setCurrentQuestionIndex(0);
            setSubmittedPartAQuestionIds(
              new Set(partAQuestions.map((question) => question.question_id))
            );
            setAnswers(new Map());
            dispatchSubmit({ type: 'RESET' });
            setState('part-b');
            resumeTimer();
          } catch {
            setState('error');
            setError('Session already submitted but could not load Part B.');
          }
        } else if (err.status === 410) {
          // Session expired — cannot continue
          dispatchSubmit({ type: 'ERROR_TERMINAL_410', message: 'Session has expired.' });
          setError('Your session has expired. Please contact your trainer to restart.');
          setState('error');
          toast.error('Session expired.');
        } else {
          dispatchSubmit({ type: 'ERROR_RECOVERABLE', message: err.message });
          toast.error('Failed to submit Part A. Please try again.');
          setState('part-a');
          resumeTimer();
        }
      } else {
        dispatchSubmit({ type: 'ERROR_RECOVERABLE', message: 'Network error. Please try again.' });
        console.error('Part A submission error:', err);
        toast.error('Failed to submit Part A. Please try again.');
        setState('part-a');
        resumeTimer();
      }
    }
  }, [sessionId, submitState, answers, pauseTimer, resumeTimer, partAQuestions, testId]);

  // Final submit handler
  const handleFinalSubmit = useCallback(async () => {
    if (!sessionId || !canSubmit(submitState)) return;

    try {
      setState('submitting');
      pauseTimer();
      dispatchSubmit({ type: 'SUBMIT' });

      const answersArray: QuizAnswer[] = Array.from(answers.entries()).map(([qId, answer]) => ({
        question_id: qId,
        selected_answers: Array.isArray(answer)
          ? answer
          : typeof answer === 'boolean'
            ? [answer ? 1 : 0]
            : [answer],
      }));

      await submitPartB({
        session_id: sessionId,
        answers: answersArray,
      });

      dispatchSubmit({ type: 'SUCCESS' });

      localStorage.removeItem(`quiz-session-${testId}`);
      localStorage.removeItem(`quiz-part-${testId}`);
      localStorage.removeItem(`quiz-answers-${testId}`);
      localStorage.removeItem(`quiz-timer-${testId}`);
      localStorage.removeItem(`quiz-draft-${sessionId}`);

      setState('completed');
      toast.success('Quiz submitted successfully! Redirecting to results...');

      setTimeout(() => {
        router.push(
          sessionId
            ? `/participant/tests/results/${sessionId}`
            : '/participant/tests'
        );
      }, 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          // Already completed — navigate away
          dispatchSubmit({ type: 'ERROR_TERMINAL_409', message: 'Quiz already submitted.' });
          setState('completed');
          toast.info('Quiz was already submitted. Redirecting...');
          setTimeout(() => router.push('/participant/tests'), 2000);
        } else if (err.status === 410) {
          // Session expired — show terminal error
          dispatchSubmit({ type: 'ERROR_TERMINAL_410', message: 'Session has expired.' });
          setError('Your session has expired. Your answers could not be submitted.');
          setState('error');
          toast.error('Session expired. Please contact your trainer.');
        } else {
          dispatchSubmit({ type: 'ERROR_RECOVERABLE', message: err.message });
          toast.error('Failed to submit quiz. Please try again.');
          setState('part-b');
          resumeTimer();
        }
      } else {
        dispatchSubmit({ type: 'ERROR_RECOVERABLE', message: 'Network error. Please try again.' });
        console.error('Final submission error:', err);
        toast.error('Failed to submit quiz. Please try again.');
        setState('part-b');
        resumeTimer();
      }
    }
  }, [sessionId, submitState, answers, pauseTimer, resumeTimer, testId, router]);

  // Auto-submit handler — declared after its dependencies
  const handleTimeExpired = useCallback(async () => {
    toast.error('Time expired! Auto-submitting your quiz...');

    if (currentPart === 'A' && sessionId) {
      await handleSubmitPartA();
    } else if (currentPart === 'B' && sessionId) {
      await handleFinalSubmit();
    }
  }, [currentPart, sessionId, handleSubmitPartA, handleFinalSubmit]);

  // Keep ref in sync so useTimer always calls the latest handleTimeExpired
  useEffect(() => {
    handleTimeExpiredRef.current = handleTimeExpired;
  }, [handleTimeExpired]);

  // Load test data and create session
  useEffect(() => {
    if (isNaN(testId) || isNaN(submissionId)) return;

    const initializeQuiz = async () => {
      try {
        setState('loading');
        setPartAQuestions([]);
        setPartBQuestions([]);
        setSubmittedPartAQuestionIds(new Set());
        setAnswers(new Map());
        setCurrentQuestionIndex(0);

        localStorage.removeItem(`quiz-session-${testId}`);
        localStorage.removeItem(`quiz-part-${testId}`);
        localStorage.removeItem(`quiz-answers-${testId}`);
        localStorage.removeItem(`quiz-timer-${testId}`);

        const testData = await getTest(testId);
        setTest(testData);

        const durationSeconds = testData.duration_seconds || 7200;

        const currentUser = await getCurrentUser();
        const userId = currentUser.id;

        const session = await createTestSession({
          test_id: testId,
          submission_id: submissionId,
          user_id: userId,
          total_questions: testData.number_of_questions,
        });

        const activeSessionId = session.session_id || session.id || null;
        if (!activeSessionId) {
          throw new Error('Session ID is missing from session response');
        }
        setSessionId(activeSessionId);
        setCurrentPart('A');

        // Use server-computed expires_at as the authoritative deadline.
        // Append Z if missing — backend serializes naive utcnow() without timezone suffix,
        // and Date.parse treats no-timezone strings as local time on most browsers.
        const raw = session.expires_at;
        const expiresAtMs = raw
          ? Date.parse(raw.endsWith('Z') || raw.includes('+') ? raw : raw + 'Z')
          : undefined;
        resetTimer(durationSeconds, expiresAtMs);

        localStorage.setItem(`quiz-session-${testId}`, activeSessionId);
        localStorage.setItem(`quiz-part-${testId}`, 'A');

        const partAData = await getPartAQuestions(activeSessionId);

        setPartAQuestions(partAData.questions);
        setQuestions(partAData.questions);

        // Rehydrate draft answers from server if session has a saved draft
        if (session.draft_answers && session.draft_answers.length > 0) {
          const rehydrated = new Map<string, AnswerValue>();
          for (const entry of session.draft_answers) {
            const v = entry.answer;
            rehydrated.set(entry.question_id, Array.isArray(v) ? v : (v as AnswerValue));
          }
          setAnswers(rehydrated);
        }

        setState('part-a');

        toast.success('Quiz loaded successfully!');
      } catch (err) {
        console.error('Quiz initialization error:', err);
        setError(err instanceof Error ? err.message : 'Failed to initialize quiz');
        setState('error');
        toast.error('Failed to load quiz. Please try again.');
      }
    };

    initializeQuiz();
  }, [testId, submissionId, resetTimer]);

  // Save answers to localStorage whenever they change
  useEffect(() => {
    if (isNaN(testId) || answers.size === 0) return;
    const answersObj = Object.fromEntries(answers);
    localStorage.setItem(`quiz-answers-${testId}`, JSON.stringify(answersObj));
  }, [answers, testId]);

  // ─── CONDITIONAL RETURNS (safe after all hooks) ──────────────────────────────

  if (isNaN(testId)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Invalid Test ID</h2>
                <p className="mt-2 text-sm text-slate-600">
                  The test ID in the URL is invalid. Received: &quot;{resolvedParams.testId}&quot;
                </p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isNaN(submissionId)) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="mx-auto mb-4 h-12 w-12 text-amber-500" />
            <h2 className="mb-2 text-lg font-semibold">Missing submission ID</h2>
            <p className="mb-4 text-sm text-slate-600">No valid submission was linked to this quiz URL.</p>
            <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─── HANDLERS ────────────────────────────────────────────────────────────────

  const handleAnswerChange = (questionId: string, answer: AnswerValue) => {
    setAnswers((prev) => {
      const newAnswers = new Map(prev);
      newAnswers.set(questionId, answer);
      return newAnswers;
    });
  };

  const handleNavigate = (questionId: string, targetPart: Part) => {
    if (targetPart !== currentPart) return;

    const sourceQuestions = targetPart === 'A' ? partAQuestions : partBQuestions;
    const targetIndex = sourceQuestions.findIndex(
      (question) => question.question_id === questionId
    );

    if (targetIndex !== -1) {
      setCurrentQuestionIndex(targetIndex);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handleConfirmSubmit = () => {
    if (!canSubmit(submitState)) return;

    const unansweredCount = questions.length - currentPartAnsweredCount;

    if (unansweredCount > 0) {
      const confirmed = window.confirm(
        `You have ${unansweredCount} unanswered question(s). Are you sure you want to submit?`
      );
      if (!confirmed) return;
    }

    if (currentPart === 'A') {
      handleSubmitPartA();
    } else {
      handleFinalSubmit();
    }
  };

  // ─── RENDER ──────────────────────────────────────────────────────────────────

  if (state === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <div className="size-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
              <p className="text-center text-sm text-slate-600">Loading quiz...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (state === 'error') {
    const isExpired = isTerminalError(submitState) && submitState.status === 'error_terminal_410';
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">
                  {isExpired ? 'Session Expired' : 'Error Loading Quiz'}
                </h2>
                <p className="mt-2 text-sm text-slate-600">{error}</p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (state === 'transitioning') {
    return <PartTransition message="Submitting Part A and loading Part B..." />;
  }

  if (state === 'submitting') {
    return <PartTransition message="Submitting your quiz..." />;
  }

  if (state === 'completed') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-green-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <CheckCircle2 className="size-12 text-green-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Quiz Submitted!</h2>
                <p className="mt-2 text-sm text-slate-600">Redirecting to results...</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const totalQuestionCount =
    derivedTotalQuestions != null
      ? derivedTotalQuestions
      : partAQuestions.length + (expectedPartBCount || partBQuestions.length);
  const overallQuestionCount = totalQuestionCount > 0 ? totalQuestionCount : questions.length;

  const submitDisabled = !canSubmit(submitState);
  const submitLabel = submitState.status === 'submitting'
    ? 'Submitting…'
    : currentPart === 'A'
      ? 'Submit Part A'
      : 'Submit Quiz';

  return (
    <div className="min-h-screen bg-slate-50 pb-8">
      <ProgressHeader
        part={currentPart}
        currentQuestionNumber={currentQuestionIndex + 1}
        answeredCount={answeredCount}
        totalQuestions={questions.length}
        overallQuestionCount={overallQuestionCount}
        testName={test?.name || 'Quiz'}
        testRole={test?.role}
        onPrevious={handlePrevious}
        onNext={handleNext}
        hasPrevious={currentQuestionIndex > 0}
        hasNext={currentQuestionIndex < questions.length - 1}
      />

      <div className="container mx-auto mt-6 px-4">
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <div className="space-y-6">
            {currentQuestion && (
              <QuestionCard
                question={currentQuestion}
                questionNumber={currentQuestionIndex + 1}
                selectedAnswer={answers.get(currentQuestion.question_id) ?? null}
                onAnswerChange={(answer) =>
                  handleAnswerChange(currentQuestion.question_id, answer)
                }
              />
            )}

            {/* Recoverable error banner */}
            {submitState.status === 'error_recoverable' && (
              <Card className="border-amber-200 bg-amber-50">
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-amber-800">
                    <AlertCircle className="mr-1 inline size-4" />
                    {submitState.message} — please try again.
                  </p>
                </CardContent>
              </Card>
            )}

            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {currentPart === 'A' ? 'Ready to submit Part A?' : 'Ready to submit your quiz?'}
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      {currentPartAnsweredCount} of {questions.length} questions answered in Part{' '}
                      {currentPart}
                    </p>
                  </div>
                  <Button
                    onClick={handleConfirmSubmit}
                    size="lg"
                    disabled={submitDisabled}
                  >
                    {submitState.status === 'submitting' && (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    )}
                    {submitLabel}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4 lg:sticky lg:top-24 lg:self-start">
            <Timer
              timeRemaining={timer.timeRemaining}
              formatTime={timer.formatTime}
              isWarning={timer.isWarning}
              isCritical={timer.isCritical}
            />

            <QuestionNavigation
              currentPart={currentPart}
              currentQuestionId={currentQuestion?.question_id ?? null}
              partAQuestions={partAQuestions}
              partBQuestions={partBQuestionsForNavigation}
              answeredQuestionIds={answeredQuestionIds}
              onNavigate={handleNavigate}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
