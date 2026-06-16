import { Suspense } from 'react';
import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { getSession } from '@/lib/session';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import ResultsSkeleton from '@/components/results/ResultsSkeleton';
import ResultsChart from '@/components/results/ResultsChart';
import type { TestSession, GradedQuizQuestion } from '@/lib/api/types';

const API_GATEWAY = process.env.API_GATEWAY_URL ?? 'http://localhost:8000';

async function fetchSession(sessionId: string, token: string): Promise<TestSession> {
  const res = await fetch(`${API_GATEWAY}/v1/api/test-sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`Session fetch failed: ${res.status}`);
  const raw = await res.json();
  return { ...raw, session_id: raw.id ?? raw.session_id };
}

interface Props {
  params: Promise<{ sessionId: string }>;
}

async function ResultsContent({ sessionId }: { sessionId: string }) {
  const session = await getSession();
  if (!session) redirect('/');

  const data = await fetchSession(sessionId, session.token);

  const partA: GradedQuizQuestion[] = data.part_a?.questions ?? [];
  const partB: GradedQuizQuestion[] = data.part_b?.questions ?? [];
  const allQuestions = [...partA, ...partB];

  const totalCount = allQuestions.length;
  const correctCount = allQuestions.filter((q) => q.is_correct).length;
  const incorrectCount = totalCount - correctCount;
  const score = data.percentage_score ?? 0;
  const passed = score >= 70;

  const partAScore = data.part_a?.score;
  const partBScore = data.part_b?.score;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <Link href="/participant/tests" className="hover:text-slate-700 transition-colors">
              My Tests
            </Link>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-slate-400">Results</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">Quiz Results</h1>
          {data.completed_at && (
            <p className="text-sm text-slate-500">
              Completed {new Date(data.completed_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric',
              })}
            </p>
          )}
        </div>
        <Badge
          variant={passed ? 'default' : 'destructive'}
          className="rounded-full px-4 py-1 text-xs font-semibold"
        >
          {passed ? 'Passed' : 'Failed'}
        </Badge>
      </section>

      {/* Score card */}
      <Card className={passed ? 'border-green-200 bg-green-50/40' : 'border-red-200 bg-red-50/40'}>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-6">
            <div
              className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-2xl font-bold ${
                passed
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'
              }`}
              aria-label={`Score: ${Math.round(score)} percent`}
            >
              {Math.round(score)}%
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-500">Overall Score</p>
              <p className="text-4xl font-bold text-slate-900">{Math.round(score)}%</p>
              <p className="text-sm text-slate-500">
                {correctCount} of {totalCount} questions correct
              </p>
            </div>
            {(partAScore != null || partBScore != null) && (
              <div className="ml-auto flex gap-4 text-sm text-slate-600">
                {partAScore != null && (
                  <div className="text-center">
                    <p className="font-semibold text-slate-900">{Math.round(partAScore * 100)}%</p>
                    <p className="text-xs text-slate-500">Part A</p>
                  </div>
                )}
                {partBScore != null && (
                  <div className="text-center">
                    <p className="font-semibold text-slate-900">{Math.round(partBScore * 100)}%</p>
                    <p className="text-xs text-slate-500">Part B</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Total Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-semibold text-slate-900">{totalCount}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-600">Correct</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-semibold text-green-700">{correctCount}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-500">Incorrect</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-semibold text-red-600">{incorrectCount}</span>
          </CardContent>
        </Card>
      </div>

      {/* Per-question chart */}
      {totalCount > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Time Per Question</CardTitle>
            <CardDescription>
              Green bars = correct &nbsp;·&nbsp; Red bars = incorrect
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResultsChart partA={partA} partB={partB} />
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button asChild variant="default">
          <Link href="/participant/tests">Back to Tests</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/participant/dashboard">Dashboard</Link>
        </Button>
      </div>
    </div>
  );
}

export default function ResultsPage({ params }: Props) {
  return (
    <Suspense fallback={<ResultsSkeleton />}>
      <ResultsContentWrapper params={params} />
    </Suspense>
  );
}

async function ResultsContentWrapper({ params }: Props) {
  const { sessionId } = await params;
  return <ResultsContent sessionId={sessionId} />;
}
