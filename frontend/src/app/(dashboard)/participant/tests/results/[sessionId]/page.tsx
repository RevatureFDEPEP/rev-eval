import { Suspense } from 'react';
import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { getSession } from '@/lib/session';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import ResultsSkeleton from '@/components/results/ResultsSkeleton';
import ResultsChart from '@/components/results/ResultsChart';
import type { UserSummaryResponse, AttemptsResponse, UserSessionEntry } from '@/lib/api/types';

const API_GATEWAY = process.env.API_GATEWAY_URL ?? 'http://localhost:8000';

async function fetchSummary(userId: number, token: string): Promise<UserSummaryResponse> {
  const res = await fetch(`${API_GATEWAY}/v1/api/reports/user/${userId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`Summary fetch failed: ${res.status}`);
  return res.json();
}

async function fetchAttempts(userId: number, token: string): Promise<AttemptsResponse> {
  const res = await fetch(`${API_GATEWAY}/v1/api/reports/user/${userId}/attempts?size=50&sort=completed_at:desc`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Attempts fetch failed: ${res.status}`);
  return res.json();
}

interface Props {
  params: Promise<{ sessionId: string }>;
}

async function ResultsContent({ sessionId }: { sessionId: string }) {
  const session = await getSession();
  if (!session) redirect('/');

  const [summary, attemptsData] = await Promise.all([
    fetchSummary(session.userId, session.token),
    fetchAttempts(session.userId, session.token),
  ]);

  const attempts: UserSessionEntry[] = attemptsData.attempts ?? [];
  const current = attempts.find((a) => a.session_id === sessionId) ?? attempts[0];

  const score = current?.percentage_score ?? 0;
  const passed = score >= 70;
  const completedAt = current?.completed_at;

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
          {completedAt && (
            <p className="text-sm text-slate-500">
              Completed {new Date(completedAt).toLocaleDateString('en-US', {
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
              <p className="text-sm font-medium text-slate-500">This Attempt</p>
              <p className="text-4xl font-bold text-slate-900">{Math.round(score)}%</p>
              {current?.total_questions != null && (
                <p className="text-sm text-slate-500">
                  {current.total_questions} questions
                </p>
              )}
            </div>
            <div className="ml-auto flex gap-6 text-sm text-slate-600">
              {summary.best_score != null && (
                <div className="text-center">
                  <p className="font-semibold text-slate-900">{Math.round(summary.best_score)}%</p>
                  <p className="text-xs text-slate-500">Best</p>
                </div>
              )}
              {summary.avg_score != null && (
                <div className="text-center">
                  <p className="font-semibold text-slate-900">{Math.round(summary.avg_score)}%</p>
                  <p className="text-xs text-slate-500">Average</p>
                </div>
              )}
              <div className="text-center">
                <p className="font-semibold text-slate-900">{summary.total_attempts}</p>
                <p className="text-xs text-slate-500">Attempts</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-attempt history chart */}
      {attempts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Score History</CardTitle>
            <CardDescription>
              Green bars = passed (≥70%) &nbsp;·&nbsp; Red bars = failed &nbsp;·&nbsp; Highlighted = this attempt
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResultsChart attempts={attempts} currentSessionId={sessionId} />
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
