'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth/useAuth';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrainerCharts } from '@/components/trainer/TrainerCharts';
import { getTrainerDashboardStats, getTrainerTests } from '@/lib/api';
import type { TrainerTestInfo } from '@/lib/api/types';

type TrainerStats = {
  active_tests_count: number;
  total_participants_count: number;
  pending_submissions_count: number;
  quiz_tests_count: number;
  interview_tests_count: number;
  total_submissions: number;
  completed_submissions: number;
};

export default function TrainerDashboard() {
  const { user, loading: authLoading } = useAuth({ ensureSignedIn: true });

  const [stats, setStats] = useState<TrainerStats>({
    active_tests_count: 0,
    total_participants_count: 0,
    pending_submissions_count: 0,
    quiz_tests_count: 0,
    interview_tests_count: 0,
    total_submissions: 0,
    completed_submissions: 0,
  });
  const [tests, setTests] = useState<TrainerTestInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;

    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [statsData, testsData] = await Promise.all([
          getTrainerDashboardStats(),
          getTrainerTests(),
        ]);

        setStats((prev) => ({ ...prev, ...statsData }));
        setTests(testsData);
      } catch (err: unknown) {
        console.error('Dashboard error:', err);
        const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [user, authLoading]);

  if (authLoading || !user) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-4 text-sm text-slate-600">Getting things ready…</p>
        </div>
      </div>
    );
  }

  const completionRate = stats.total_submissions > 0
    ? Math.round((stats.completed_submissions / stats.total_submissions) * 100)
    : 0;

  const chartStats = {
    quiz_tests_count: stats.quiz_tests_count ?? 0,
    interview_tests_count: stats.interview_tests_count ?? 0,
  };

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Trainer workspace</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline" />
            <span className="text-slate-400">Overview</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">Dashboard</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Monitor performance across your cohorts, track completion trends, and keep an eye on student progress.
          </p>
        </div>
        <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
          Trainer
        </Badge>
      </section>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-sm text-red-800">
              <strong>Error:</strong> {error}. Please verify the backend services are online.
            </p>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm text-slate-500">
          Loading dashboard insights…
        </div>
      ) : (
        <>
          <section className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card className="border border-orange-100/70 bg-white/95 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lg">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Active Tests</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.active_tests_count}</div>
                <p className="text-xs text-slate-500">
                  {stats.quiz_tests_count} Quiz · {stats.interview_tests_count} Interview
                </p>
              </CardContent>
            </Card>

            <Card className="border border-purple-100/70 bg-white/95 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lg">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Assigned Tests</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.pending_submissions_count}</div>
                <p className="text-xs text-slate-500">
                  {stats.pending_submissions_count > 0 ? 'Awaiting completion' : 'All caught up'}
                </p>
              </CardContent>
            </Card>

            <Card className="border border-purple-100/70 bg-white/95 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lg">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Total Participants</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.total_participants_count}</div>
                <p className="text-xs text-slate-500">{stats.total_submissions} total assignments</p>
              </CardContent>
            </Card>

            <Card className="border border-orange-100/70 bg-white/95 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lg">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Completion Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{completionRate}%</div>
                <p className="text-xs text-slate-500">
                  {stats.completed_submissions} / {stats.total_submissions} completed
                </p>
              </CardContent>
            </Card>
          </section>

          <TrainerCharts stats={chartStats} tests={tests} />
        </>
      )}
    </div>
  );
}
