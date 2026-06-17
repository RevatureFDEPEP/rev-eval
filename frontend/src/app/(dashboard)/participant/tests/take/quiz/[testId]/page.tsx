'use client';

/**
 * Server-backed quiz-taking page.
 *
 * Drives the `/v1/api/sessions` contract: the session is durable and
 * server-timed, every answer is scored + recorded server-side (idempotently),
 * and the countdown is derived from the server's `expires_at` rather than a
 * local-only clock. Attempt state lives on the server, not localStorage.
 */
import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import {
  createQuizSession,
  getQuizSession,
  saveQuizDraft,
  submitQuizAnswer,
  submitQuizSession,
  quizErrorStatus,
  type QuizQuestionOut,
  type QuizSubmitResult,
  type SelectedAnswer,
} from '@/lib/api/quiz';

type Phase = 'loading' | 'active' | 'submitting' | 'done' | 'error' | 'locked';

interface PageProps {
  params: Promise<{ testId: string }>;
}

function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export default function QuizTakePage({ params }: PageProps) {
  const resolved = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const testId = parseInt(resolved.testId, 10);
  const submissionRaw = searchParams.get('submission');
  const submissionId = submissionRaw ? parseInt(submissionRaw, 10) : undefined;

  const [phase, setPhase] = useState<Phase>('loading');
  const [error, setError] = useState<string | null>(null);
  const [lockedMessage, setLockedMessage] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuizQuestionOut[]>([]);
  const [answers, setAnswers] = useState<Record<string, SelectedAnswer[]>>({});
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<QuizSubmitResult | null>(null);
  const [remaining, setRemaining] = useState<number>(0);

  // Server clock skew: deadline expressed in the browser's monotonic time.
  const deadlineRef = useRef<number | null>(null);
  const initOnce = useRef(false);

  const handleSubmitSession = useCallback(
    async (auto: boolean) => {
      if (!sessionId) return;
      setPhase('submitting');
      try {
        const res = await submitQuizSession(sessionId);
        setResult(res);
        setPhase('done');
        if (auto) toast.warning('Time expired — your quiz was submitted automatically.');
        // Land on the durable, deep-linkable results page for this attempt.
        router.push(`/participant/tests/results/${sessionId}`);
      } catch (err) {
        const code = quizErrorStatus(err);
        if (code === 409) {
          // Already finalized/expired server-side — treat as terminal.
          try {
            const state = await getQuizSession(sessionId);
            setResult({
              session_id: state.session_id,
              status: state.status,
              submitted_at: state.server_now,
              total_score: state.total_score ?? 0,
              max_score: state.max_score ?? 0,
              percentage_score: state.percentage_score ?? 0,
              correct_count: 0,
              answered_count: Object.keys(state.draft_answers || {}).length,
              total_questions: state.total_questions,
            });
            setPhase('done');
            router.push(`/participant/tests/results/${sessionId}`);
            return;
          } catch {
            /* fall through */
          }
        }
        toast.error('Could not submit the quiz. Please try again.');
        setPhase('active');
      }
    },
    [sessionId, router],
  );

  const handleSubmitRef = useRef(handleSubmitSession);
  useEffect(() => {
    handleSubmitRef.current = handleSubmitSession;
  }, [handleSubmitSession]);

  // ---- Initialize the session ----
  useEffect(() => {
    if (initOnce.current) return;
    initOnce.current = true;

    (async () => {
      if (isNaN(testId)) {
        setError('Invalid test id in URL.');
        setPhase('error');
        return;
      }
      try {
        const start = await createQuizSession({
          test_id: testId,
          submission_id: submissionId ?? null,
        });
        setSessionId(start.session_id);

        // Pull full state (all safe questions + any resumed draft).
        const state = await getQuizSession(start.session_id);
        setQuestions(state.questions);
        setAnswers(state.draft_answers || {});
        setIndex(state.current_index || 0);

        const serverNow = new Date(state.server_now).getTime();
        const expiresAt = new Date(state.expires_at).getTime();
        deadlineRef.current = Date.now() + (expiresAt - serverNow);
        setRemaining((expiresAt - serverNow) / 1000);
        setPhase('active');
      } catch (err) {
        const code = quizErrorStatus(err);
        if (code === 401) setError('You are not authorized to start this quiz.');
        else if (code === 403) setError('This test is not available to start.');
        else setError('Failed to start the quiz session.');
        setPhase('error');
      }
    })();
  }, [testId, submissionId]);

  // ---- Server-authoritative countdown ----
  useEffect(() => {
    if (phase !== 'active' || deadlineRef.current == null) return;
    const tick = () => {
      const left = (deadlineRef.current! - Date.now()) / 1000;
      setRemaining(left);
      if (left <= 0) {
        void handleSubmitRef.current(true);
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [phase]);

  const current = questions[index];

  const setSelection = useCallback(
    async (question: QuizQuestionOut, selected: SelectedAnswer[]) => {
      if (!sessionId) return;
      setAnswers((prev) => ({ ...prev, [question.question_id]: selected }));

      // Stable idempotency key per (session, question, selection) so a retry of
      // the *same* selection replays instead of double-recording.
      const idempotencyKey = `${sessionId}:${question.question_id}:${JSON.stringify(selected)}`;
      try {
        await submitQuizAnswer(
          sessionId,
          { question_id: question.question_id, selected_answers: selected },
          idempotencyKey,
        );
        // Best-effort cursor autosave; failure here is non-fatal.
        void saveQuizDraft(sessionId, { current_index: index }).catch(() => {});
      } catch (err) {
        const code = quizErrorStatus(err);
        if (code === 409) {
          setLockedMessage('This quiz is already submitted or expired.');
          setPhase('locked');
        } else if (code === 401) {
          setLockedMessage('Your session is no longer authorized.');
          setPhase('locked');
        } else {
          toast.error('Could not save your answer. Check your connection.');
        }
      }
    },
    [sessionId, index],
  );

  const answeredCount = useMemo(
    () => Object.values(answers).filter((v) => v && v.length > 0).length,
    [answers],
  );

  // ---------- render ----------
  if (phase === 'loading') {
    return <Centered><Spinner /><p className="text-sm text-slate-600">Starting quiz…</p></Centered>;
  }

  if (phase === 'error') {
    return (
      <Centered>
        <AlertCircle className="size-12 text-red-600" />
        <h2 className="text-lg font-semibold">Cannot start quiz</h2>
        <p className="text-sm text-slate-600">{error}</p>
        <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
      </Centered>
    );
  }

  if (phase === 'locked') {
    return (
      <Centered>
        <AlertCircle className="size-12 text-amber-600" />
        <h2 className="text-lg font-semibold">Quiz locked</h2>
        <p className="text-sm text-slate-600">{lockedMessage}</p>
        <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
      </Centered>
    );
  }

  if (phase === 'done' && result) {
    return (
      <Centered>
        <CheckCircle2 className="size-12 text-green-600" />
        <h2 className="text-lg font-semibold">Quiz submitted</h2>
        <p className="text-sm text-slate-600">
          Score: {result.total_score} / {result.max_score} (
          {result.percentage_score.toFixed(1)}%) · {result.correct_count} correct of{' '}
          {result.total_questions}
        </p>
        <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
      </Centered>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">
          Question {index + 1} of {questions.length} · {answeredCount} answered
        </p>
        <span
          className={`flex items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold ${
            remaining <= 60 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'
          }`}
        >
          <Clock className="size-4" /> {formatClock(remaining)}
        </span>
      </div>

      {current && (
        <Card>
          <CardContent className="space-y-4 pt-6">
            <p className="font-medium text-slate-900">{current.question_text}</p>
            <QuestionInput
              question={current}
              selected={answers[current.question_id] || []}
              onChange={(sel) => setSelection(current, sel)}
            />
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          disabled={index === 0}
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
        >
          Previous
        </Button>
        {index < questions.length - 1 ? (
          <Button onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}>
            Next
          </Button>
        ) : (
          <Button
            disabled={phase === 'submitting'}
            onClick={() => {
              const unanswered = questions.length - answeredCount;
              if (unanswered > 0 && !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)) {
                return;
              }
              void handleSubmitSession(false);
            }}
          >
            {phase === 'submitting' ? 'Submitting…' : 'Submit Quiz'}
          </Button>
        )}
      </div>
    </div>
  );
}

function QuestionInput({
  question,
  selected,
  onChange,
}: {
  question: QuizQuestionOut;
  selected: SelectedAnswer[];
  onChange: (selected: SelectedAnswer[]) => void;
}) {
  const type = question.question_type.toLowerCase();

  if (type === 'true_false') {
    return (
      <div className="flex gap-3">
        {[true, false].map((val) => (
          <Button
            key={String(val)}
            variant={selected[0] === val ? 'default' : 'outline'}
            onClick={() => onChange([val])}
          >
            {val ? 'True' : 'False'}
          </Button>
        ))}
      </div>
    );
  }

  const options = question.options || [];
  // Options are 1-indexed positions in the backend's answer model.
  return (
    <div className="space-y-2">
      {options.map((opt, i) => {
        const pos = i + 1;
        const isMulti = type === 'multi';
        const checked = selected.includes(pos);
        const label = String((opt as { text?: string }).text ?? `Option ${pos}`);
        return (
          <label
            key={pos}
            className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm ${
              checked ? 'border-blue-500 bg-blue-50' : 'border-slate-200'
            }`}
          >
            <input
              type={isMulti ? 'checkbox' : 'radio'}
              name={question.question_id}
              checked={checked}
              onChange={() => {
                if (isMulti) {
                  const next = checked
                    ? selected.filter((s) => s !== pos)
                    : [...selected.filter((s) => typeof s === 'number'), pos];
                  onChange(next as SelectedAnswer[]);
                } else {
                  onChange([pos]);
                }
              }}
            />
            <span>{label}</span>
          </label>
        );
      })}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-4 pt-6 text-center">
          {children}
        </CardContent>
      </Card>
    </div>
  );
}

function Spinner() {
  return (
    <div className="size-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
  );
}
