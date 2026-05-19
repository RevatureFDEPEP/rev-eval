'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth/useAuth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { AssociateCharts } from '@/components/associate/AssociateCharts';
import { getAssociateDashboardStats, getAssignedTests } from '@/lib/api';
import type { AssignedTestInfo, ParticipantDashboardStats } from '@/lib/api/types';
import { SubmissionStatus, TestType } from '@/lib/api/types';
import { formatTableDate } from '@/lib/utils/date';

type AssociateStats = ParticipantDashboardStats;

export default function AssociateDashboard() {
  const { user, loading: authLoading } = useAuth({ ensureSignedIn: true });

  const [stats, setStats] = useState<AssociateStats>({
    assigned_tests_count: 0,
    completed_tests_count: 0,
    in_progress_tests_count: 0,
    average_score: 0,
    tests_due_this_week: 0,
  });
  const [assignedTests, setAssignedTests] = useState<AssignedTestInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;

    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [statsData, testsData] = await Promise.all([
          getAssociateDashboardStats(),
          getAssignedTests(),
        ]);

        setStats(statsData);
        setAssignedTests(testsData);
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
          <p className="mt-4 text-sm text-slate-600">Loading your dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Participant workspace
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">My Dashboard</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Track your assignments, view progress, and stay on top of upcoming evaluations.
          </p>
        </div>
        <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
          Participant
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
          <Card className="border-dashed border-purple-200/80 bg-white/90 shadow-none">
            <CardHeader>
              <CardTitle>Learning Progress</CardTitle>
              <CardDescription>Coming soon</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-600">
              <p>Track your learning progress across skills and modules as you complete tests.</p>
              <p className="text-xs text-slate-500">
                Upcoming features: skill-based progress tracking, learning paths, and personalized recommendations.
              </p>
            </CardContent>
          </Card>

          <section className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Upcoming Tests</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.tests_due_this_week}</div>
                <p className="text-xs text-slate-500">Due this week</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Completed</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.completed_tests_count}</div>
                <p className="text-xs text-slate-500">Tests finished</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Average Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">
                  {stats.average_score ? `${Math.round(stats.average_score)}%` : 'N/A'}
                </div>
                <p className="text-xs text-slate-500">Overall performance</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">In Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-slate-900">{stats.in_progress_tests_count}</div>
                <p className="text-xs text-slate-500">Currently taking</p>
              </CardContent>
            </Card>
          </section>

          <AssociateCharts stats={stats} assignedTests={assignedTests} />

          <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Upcoming Tests</CardTitle>
                <CardDescription>Stay prepared for what&apos;s next</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {assignedTests.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No tests assigned yet. Check back later!
                  </p>
                ) : (
                  assignedTests.slice(0, 3).map((test) => {
                    const isQuiz = test.test_type === TestType.QUIZ;
                    const href = isQuiz
                      ? `/participant/tests/take/mcq/${test.test_id}`
                      : `/participant/tests/take/interview/${test.test_id}`;

                    return (
                      <div key={test.submission_id} className="rounded-lg border border-slate-200 p-4">
                        <div className="mb-2 flex items-start justify-between">
                          <h3 className="font-medium text-slate-900">{test.test_name}</h3>
                          <Badge variant={isQuiz ? 'default' : 'secondary'}>
                            {isQuiz ? 'Quiz' : 'Interview'}
                          </Badge>
                        </div>
                        <p className="mb-2 text-sm text-slate-500">
                          {test.duration_seconds ? `${Math.round(test.duration_seconds / 60)} minutes` : 'No time limit'}
                        </p>
                        <p className="mb-2 text-sm text-slate-500">
                          Status: <Badge variant="outline">{test.status}</Badge>
                        </p>
                        {test.due_date && (
                          <p className="mb-2 text-sm text-slate-500">
                            Due: {formatTableDate(test.due_date).split(',')[0]}
                          </p>
                        )}
                        {test.status === SubmissionStatus.ASSIGNED && (
                          <Button className="mt-3 w-full" size="sm" asChild>
                            <Link href={href}>
                              {isQuiz ? 'Start Test' : 'Start Interview'}
                            </Link>
                          </Button>
                        )}
                        {test.status === SubmissionStatus.IN_PROGRESS && (
                          <Button className="mt-3 w-full" size="sm" variant="outline" asChild>
                            <Link href={href}>Continue Test</Link>
                          </Button>
                        )}
                        {(test.status === SubmissionStatus.GRADED || test.status === SubmissionStatus.COMPLETED) && 
                         (test.final_score != null || test.ai_score != null) && (
                          <div className="mt-3">
                            <Badge variant="secondary">
                              {test.status === SubmissionStatus.GRADED ? 'Graded' : 'Completed'} · 
                              Score: {Math.round(test.final_score ?? test.ai_score ?? 0)}%
                            </Badge>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
                {assignedTests.length > 3 && (
                  <Button variant="link" className="w-full p-0 text-sm" asChild>
                    <Link href="/participant/tests">View all {assignedTests.length} tests →</Link>
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Results</CardTitle>
                <CardDescription>Your latest completions</CardDescription>
              </CardHeader>
              <CardContent>
                {assignedTests.filter(test => 
                  test.status === SubmissionStatus.GRADED && 
                  (test.final_score != null || test.ai_score != null)
                ).length > 0 ? (
                  <div className="space-y-3 text-sm">
                    {assignedTests
                      .filter(test => 
                        test.status === SubmissionStatus.GRADED && 
                        (test.final_score != null || test.ai_score != null)
                      )
                      .slice(0, 3)
                      .map((test) => (
                        <div key={test.submission_id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-slate-900">{test.test_name}</p>
                            <p className="text-xs text-slate-500">
                              Completed {test.submitted_at ? formatTableDate(test.submitted_at).split(',')[0] : 'recently'}
                            </p>
                          </div>
                          <Badge variant="secondary">{Math.round(test.final_score!)}%</Badge>
                        </div>
                      ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">
                    No completed tests yet. Your results will appear here once you finish a test.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
