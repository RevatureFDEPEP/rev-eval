'use client';

/**
 * Quiz results page — `/participant/tests/results/[sessionId]`.
 *
 * Deep-linkable and refresh-safe: the score is re-read from the durable,
 * server-authoritative quiz session rather than passed through navigation
 * state. Participants only ever see their own session (the backend 404s a
 * session they do not own), and no answer keys are exposed — only the
 * aggregate tally.
 */
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { getQuizSession, quizErrorStatus, type QuizSessionState } from '@/lib/api/quiz';
import { ResultsChart } from '@/components/participant/ResultsChart';
import { ResultsSkeleton } from '@/components/participant/ResultsSkeleton';

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

function answeredCountOf(state: QuizSessionState): number {
  return Object.values(state.draft_answers || {}).filter((v) => v && v.length > 0).length;
}

export default function QuizResultsPage({ params }: PageProps) {
  const { sessionId } = use(params);
  const router = useRouter();

  const [state, setState] = useState<QuizSessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getQuizSession(sessionId);
        if (!cancelled) {
          setState(data);
          setLoading(false);
        }
      } catch (err) {
        if (cancelled) return;
        const code = quizErrorStatus(err);
        if (code === 401) setError('You are not authorized to view this result.');
        else if (code === 404) setError('We could not find that quiz result.');
        else setError('Failed to load your quiz result.');
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (loading) return <ResultsSkeleton />;

  if (error || !state) {
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-3xl items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 pt-6 text-center">
            <AlertCircle className="size-12 text-red-600" />
            <h2 className="text-lg font-semibold">Result unavailable</h2>
            <p className="text-sm text-slate-600">{error}</p>
            <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const totalScore = state.total_score ?? 0;
  const maxScore = state.max_score ?? 0;
  const percentage = state.percentage_score ?? 0;
  const answered = answeredCountOf(state);
  // Auto-scored MCQ awards one point per correct answer, so rounded points are
  // the correct-answer count. Bounded so a partial-credit edge can't exceed it.
  const correctCount = Math.min(state.total_questions, Math.round(totalScore));
  const isFinalized = state.status === 'submitted' || state.status === 'expired';

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-emerald-600">
          <CheckCircle2 className="size-5" />
          <span className="text-sm font-semibold uppercase tracking-wide">Quiz submitted</span>
        </div>
        <h1 className="text-3xl font-semibold text-slate-900">Your Results</h1>
        <p className="text-sm text-slate-500">
          {isFinalized
            ? 'Here is how you did on this attempt.'
            : 'This attempt is not finalized yet — the score below may change.'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Score Breakdown</CardTitle>
          <CardDescription>Correct, incorrect, and unanswered questions</CardDescription>
        </CardHeader>
        <CardContent>
          <ResultsChart
            percentageScore={percentage}
            totalScore={totalScore}
            maxScore={maxScore}
            correctCount={correctCount}
            answeredCount={answered}
            totalQuestions={state.total_questions}
          />
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/participant/tests">
            <ArrowLeft className="mr-2 size-4" />
            Back to Tests
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/participant/dashboard">Go to Dashboard</Link>
        </Button>
      </div>
    </div>
  );
}
