'use client';

import { useEffect, useState, useCallback, use, useMemo, useRef  } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { getTest, createTestSession, getPartAQuestions, submitPartA, getPartBQuestions, submitPartB, getCurrentUser } from '@/lib/api';
import { Test, QuizQuestion, QuizAnswer } from '@/lib/api/types';
import { useTimer } from '@/lib/hooks/useTimer';
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

// Answer type can be: number (mcq), number[] (multi), boolean (true_false)
type AnswerValue = number | number[] | boolean;

export default function QuizTestPage({ params }: QuizTestPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Use React's use() hook to unwrap Promise params in Client Component
  const resolvedParams = use(params);

  const testId = parseInt(resolvedParams.testId, 10);
  const submissionId = parseInt(searchParams.get('submission') || '', 10);

  //DECLARE ALL HOOKS FIRST - before any validation logic
  // Moved all state, memo, effect, and callback hooks above the isNaN guards.
  // Conditional returns moved to AFTER every hook call (see bottom of hook section).
  //  // State management
  const [state, setState] = useState<QuizState>('loading');
  const [test, setTest] = useState<Test | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPart, setCurrentPart] = useState<Part>('A');
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [partAQuestions, setPartAQuestions] = useState<QuizQuestion[]>([]);
  const [partBQuestions, setPartBQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [answers, setAnswers] = useState<Map<string, AnswerValue>>(new Map());
  const [submittedPartAQuestionIds, setSubmittedPartAQuestionIds] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);

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
      e.returnValue = 'You are leaving the test. Your progress may be lost and the test may be marked as abandoned. Are you sure you want to leave?';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [state]);

  // Auto-submit handler
   // ── REFS TO BREAK CIRCULAR DEPENDENCY ────────────────────────────────────
  // handleTimeExpired is passed to useTimer (below), but it also needs to call
  // handleSubmitPartA / handleFinalSubmit which are defined after useTimer.
  // Using refs breaks this cycle: the ref is always current by the time the
  // timer fires, but handleTimeExpired itself has no dependency on the functions.
  const submitPartARef = useRef<(() => Promise<void>) | undefined>(undefined);
  const finalSubmitRef = useRef<(() => Promise<void>) | undefined>(undefined);

  // Auto-submit handler — reads current submit functions via ref

  const handleTimeExpired = useCallback(async () => {
    toast.error('Time expired! Auto-submitting your quiz...');

    if (currentPart === 'A' && sessionId) {
      await submitPartARef.current?.();
    } else if (currentPart === 'B' && sessionId) {
      await finalSubmitRef.current?.();
    }
  }, [currentPart, sessionId]);
  // No longer depends on handleSubmitPartA / handleFinalSubmit directly,
  // eliminating both the "accessed before declaration" and missing-dep warnings.

  // Derived values

  const derivedTotalQuestions =
    typeof test?.number_of_questions === 'number' && test.number_of_questions > 0
      ? test.number_of_questions
      : undefined;

  const expectedPartBCount = useMemo(() => {
    const totalRemaining = derivedTotalQuestions != null
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
    testId: testId.toString(),
    onTimeExpired: handleTimeExpired,
    autoStart: false,
  });

  const pauseTimer = timer.pause;
  const resumeTimer = timer.resume;
  const resetTimer = timer.reset;

   // Start/pause timer based on quiz state

  useEffect(() => {
    if (state === 'part-a' || state === 'part-b') {
      resumeTimer();
    } else {
      pauseTimer();
    }
  }, [state, pauseTimer, resumeTimer]);

  // Load test data and create session
  useEffect(() => {
    const initializeQuiz = async () => {
      try {
        setState('loading');
        setPartAQuestions([]);
        setPartBQuestions([]);
        setSubmittedPartAQuestionIds(new Set());
        setAnswers(new Map());
        setCurrentQuestionIndex(0);

        // Clear any stale localStorage data for this test
        localStorage.removeItem(`quiz-session-${testId}`);
        localStorage.removeItem(`quiz-part-${testId}`);
        localStorage.removeItem(`quiz-answers-${testId}`);
        localStorage.removeItem(`quiz-timer-${testId}`);

        // Fetch test data
        const testData = await getTest(testId);
        setTest(testData);

        const durationSeconds = testData.duration_seconds || 2700;
        resetTimer(durationSeconds);

        // Get authenticated user's ID
        const currentUser = await getCurrentUser();
        const userId = currentUser.id;

        const session = await createTestSession({
          test_id: testId,
          submission_id: submissionId,
          user_id: userId,
          total_questions: testData.number_of_questions,
        });

        // Set session ID in state
        const activeSessionId = session.session_id || session.id || null;
        if (!activeSessionId) {
          throw new Error('Session ID is missing from session response');
        }
        setSessionId(activeSessionId);
        setCurrentPart('A');

        // Store session ID in localStorage for crash recovery
        localStorage.setItem(`quiz-session-${testId}`, activeSessionId);
        localStorage.setItem(`quiz-part-${testId}`, 'A');

        const partAData = await getPartAQuestions(activeSessionId);

        setPartAQuestions(partAData.questions);
        setQuestions(partAData.questions);
        setState('part-a');

        toast.success('Quiz loaded successfully!');
      } catch (err) {
        console.error('❌ Quiz initialization error:', err);

        // Log detailed error information
        if (err instanceof Error) {
          console.error('Error message:', err.message);
          console.error('Error stack:', err.stack);
        }

        setError(err instanceof Error ? err.message : 'Failed to initialize quiz');
        setState('error');
        toast.error('Failed to load quiz. Please try again.');
      }
    };

    initializeQuiz();
  }, [testId, submissionId, resetTimer]);

  // Save answers to localStorage whenever they change
  useEffect(() => {
    if (answers.size > 0) {
      const answersObj = Object.fromEntries(answers);
      localStorage.setItem(`quiz-answers-${testId}`, JSON.stringify(answersObj));
    }
  }, [answers, testId]);

  // Defined as useCallback so refs always hold a stable, up-to-date reference.
  // Submit Part A handler
  const handleSubmitPartA = useCallback(async () => {
    if (!sessionId) return;

    try {
      setState('transitioning');
      pauseTimer();

      // Convert answers to API format
      const answersArray: QuizAnswer[] = Array.from(answers.entries()).map(([qId, answer]) => ({
        question_id: qId,
        selected_answers: Array.isArray(answer)
          ? answer
          : typeof answer === 'boolean'
            ? [answer ? 1 : 0]
            : [answer],
      }));

      // Submit Part A
      await submitPartA({
        session_id: sessionId,
        answers: answersArray,
      });

      // Load Part B questions
      const partBData = await getPartBQuestions(sessionId);
      setPartBQuestions(partBData.questions);
      setQuestions(partBData.questions);
      setCurrentPart('B');
      setCurrentQuestionIndex(0);
      setSubmittedPartAQuestionIds(new Set(partAQuestions.map((question) => question.question_id)));
      setAnswers(new Map()); // Reset answers for Part B

      // Update localStorage
      localStorage.setItem(`quiz-part-${testId}`, 'B');
      localStorage.removeItem(`quiz-answers-${testId}`); // Clear Part A answers

      setState('part-b');
      resumeTimer();
      toast.success('Part A submitted! Starting Part B...');
    } catch (err) {
      console.error('Part A submission error:', err);
      toast.error('Failed to submit Part A. Please try again.');
      setState('part-a');
      resumeTimer();
    }
  }, [sessionId, answers, partAQuestions, testId, pauseTimer, resumeTimer]);

  // Keep ref current so handleTimeExpired always calls the latest version
  useEffect(() => {
    submitPartARef.current = handleSubmitPartA;
  }, [handleSubmitPartA]);

  // Final submit handler
  const handleFinalSubmit = useCallback(async () => {
    if (!sessionId) return;

    try {
      setState('submitting');
      pauseTimer();

      // Convert answers to API format
      const answersArray: QuizAnswer[] = Array.from(answers.entries()).map(([qId, answer]) => ({
        question_id: qId,
        selected_answers: Array.isArray(answer)
          ? answer
          : typeof answer === 'boolean'
            ? [answer ? 1 : 0]
            : [answer],
      }));

      // Submit Part B
      await submitPartB({
        session_id: sessionId,
        answers: answersArray
      });

      // Clear localStorage
      localStorage.removeItem(`quiz-session-${testId}`);
      localStorage.removeItem(`quiz-part-${testId}`);
      localStorage.removeItem(`quiz-answers-${testId}`);
      localStorage.removeItem(`quiz-timer-${testId}`);

      setState('completed');
      toast.success('Quiz submitted successfully! Redirecting to your tests...');

      // Redirect to tests list (results page not yet implemented)
      setTimeout(() => {
        router.push('/participant/tests');
      }, 2000);
    } catch (err) {
      console.error('Final submission error:', err);
      toast.error('Failed to submit quiz. Please try again.');
      setState('part-b');
      resumeTimer();
    }
  }, [sessionId, answers, testId, pauseTimer, resumeTimer, router]);

  // Keep ref current
  useEffect(() => {
    finalSubmitRef.current = handleFinalSubmit;
  }, [handleFinalSubmit]);

  
  // Answer change handler
  const handleAnswerChange = (questionId: string, answer: AnswerValue) => {
    setAnswers((prev) => {
      const newAnswers = new Map(prev);
      newAnswers.set(questionId, answer);
      return newAnswers;
    });
  };

  // Navigation handlers
  const handleNavigate = (questionId: string, targetPart: Part) => {
    if (targetPart !== currentPart) {
      return;
    }

    const sourceQuestions = targetPart === 'A' ? partAQuestions : partBQuestions;
    const targetIndex = sourceQuestions.findIndex((question) => question.question_id === questionId);

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


  // Fix: early returns for invalid params moved here, after all hooks.

  // Validate testId
  if (isNaN(testId)) {
    console.error('❌ Invalid testId - isNaN returned true. params.testId:', resolvedParams.testId);
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

  // Validate submissionId
  if (isNaN(submissionId)) {
    console.error('❌ Invalid submissionId - isNaN returned true. query param:', searchParams.get('submission'));
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Invalid Submission ID</h2>
                <p className="mt-2 text-sm text-slate-600">
                  Missing or invalid submission ID in URL.
                </p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  console.log('✅ testId validation passed:', testId);
  console.log('✅ submissionId validation passed:', submissionId);

  // Render loading state
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

  // Render error state
  if (state === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Error Loading Quiz</h2>
                <p className="mt-2 text-sm text-slate-600">{error}</p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render transitioning state
  if (state === 'transitioning') {
    return <PartTransition message="Submitting Part A and loading Part B..." />;
  }

  // Render submitting state
  if (state === 'submitting') {
    return <PartTransition message="Submitting your quiz..." />;
  }

  // Render completed state
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

  // Render main quiz interface
  const currentQuestion = questions[currentQuestionIndex];
  const totalQuestionCount =
    derivedTotalQuestions != null
      ? derivedTotalQuestions
      : partAQuestions.length + (expectedPartBCount || partBQuestions.length);
  const overallQuestionCount = totalQuestionCount > 0 ? totalQuestionCount : questions.length;

  return (
    <div className="min-h-screen bg-slate-50 pb-8">
      {/* Progress Header */}
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
          {/* Main Content */}
          <div className="space-y-6">
            {/* Current Question */}
            {currentQuestion && (
              <QuestionCard
                question={currentQuestion}
                questionNumber={currentQuestionIndex + 1}
                selectedAnswer={answers.get(currentQuestion.question_id) ?? null}
                onAnswerChange={(answer) => handleAnswerChange(currentQuestion.question_id, answer)}
              />
            )}

            {/* Submit Section */}
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {currentPart === 'A' ? 'Ready to submit Part A?' : 'Ready to submit your quiz?'}
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      {currentPartAnsweredCount} of {questions.length} questions answered in Part {currentPart}
                    </p>
                  </div>
                  <Button onClick={handleConfirmSubmit} size="lg">
                    {currentPart === 'A' ? 'Submit Part A' : 'Submit Quiz'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Timer and Question Navigation */}
          <div className="space-y-4 lg:sticky lg:top-24 lg:self-start">
            {/* Timer */}
            <Timer
              timeRemaining={timer.timeRemaining}
              formatTime={timer.formatTime}
              isWarning={timer.isWarning}
              isCritical={timer.isCritical}
            />

            {/* Question Navigation */}
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
