'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@workos-inc/authkit-nextjs/components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { formatTableDate, formatDueDate } from '@/lib/utils/date';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { getAssignedTests } from '@/lib/api';
import type { AssignedTestInfo } from '@/lib/api/types';
import { ParticipantTestDetailsSheet } from '@/components/participant/TestDetailsSheet';
import { SubmissionStatus, TestType } from '@/lib/api/types';
import { CalendarClock, CheckCircle2, Clock4, Eye, Play, TrendingUp } from 'lucide-react';

export default function ParticipantTestsPage() {
  const { user, loading: authLoading } = useAuth({ ensureSignedIn: true });
  const [tests, setTests] = useState<AssignedTestInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTest, setSelectedTest] = useState<AssignedTestInfo | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;

    const loadTests = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getAssignedTests();
        setTests(data);
      } catch (err: unknown) {
        console.error('Participant tests error:', err);
        const message = err instanceof Error ? err.message : 'Unable to load your tests';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    loadTests();
  }, [authLoading, user]);

  const stats = useMemo(() => {
    const assigned = tests.length;
    const inProgress = tests.filter((test) => test.status === SubmissionStatus.IN_PROGRESS).length;
    // Count COMPLETED, EVALUATED, and GRADED as completed (user has finished the test)
    const completed = tests.filter(
      (test) =>
        test.status === SubmissionStatus.COMPLETED ||
        test.status === SubmissionStatus.EVALUATED ||
        test.status === SubmissionStatus.GRADED
    ).length;
    // Only show scores for GRADED tests (COMPLETED/EVALUATED tests are still awaiting trainer review)
    const completedWithScores = tests.filter(
      (test) => test.status === SubmissionStatus.GRADED && (test.final_score != null || test.ai_score != null),
    );
    const avgScore = completedWithScores.length > 0
      ? Math.round(
          completedWithScores.reduce((acc, test) => acc + (test.final_score ?? test.ai_score ?? 0), 0) /
            completedWithScores.length,
        )
      : undefined;

    return { assigned, inProgress, completed, avgScore };
  }, [tests]);

  const upcomingTests = useMemo(
    () =>
      tests.filter(
        (test) =>
          test.status !== SubmissionStatus.COMPLETED &&
          test.status !== SubmissionStatus.EVALUATED &&
          test.status !== SubmissionStatus.GRADED &&
          test.status !== SubmissionStatus.ABANDONED,
      ),
    [tests],
  );

  const completedTests = useMemo(() => {
    const list = tests.filter(
      (test) =>
        test.status === SubmissionStatus.COMPLETED ||
        test.status === SubmissionStatus.EVALUATED ||
        test.status === SubmissionStatus.GRADED ||
        test.status === SubmissionStatus.ABANDONED,
    );

    return list
      .slice()
      .sort((a, b) => {
        const aDate = a.submitted_at ? new Date(a.submitted_at).getTime() : new Date(a.assigned_at).getTime();
        const bDate = b.submitted_at ? new Date(b.submitted_at).getTime() : new Date(b.assigned_at).getTime();
        return bDate - aDate;
      });
  }, [tests]);

  const handleOpenDetails = (test: AssignedTestInfo) => {
    setSelectedTest(test);
    setDetailsOpen(true);
  };

  const handleDetailsToggle = (open: boolean) => {
    setDetailsOpen(open);
    if (!open) {
      setSelectedTest(null);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-4 text-sm text-slate-600">Loading your assignments…</p>
        </div>
      </div>
    );
  }

  const statusLabels: Record<SubmissionStatus, string> = {
    [SubmissionStatus.ASSIGNED]: 'Assigned',
    [SubmissionStatus.IN_PROGRESS]: 'In Progress',
    [SubmissionStatus.COMPLETED]: 'Pending Review',
    [SubmissionStatus.EVALUATED]: 'Pending Review',
    [SubmissionStatus.GRADED]: 'Graded',
    [SubmissionStatus.ABANDONED]: 'Abandoned',
  };

  const renderActionLabel = (status: SubmissionStatus, isQuiz: boolean) => {
    switch (status) {
      case SubmissionStatus.ASSIGNED:
        return isQuiz ? 'Start Test' : 'Start Interview';
      case SubmissionStatus.IN_PROGRESS:
        return 'Continue';
      default:
        return 'Open';
    }
  };

  const getActionHref = (test: AssignedTestInfo, isQuiz: boolean) => {
    // Validate test_id and submission_id exist
    if (!test.test_id || isNaN(test.test_id)) {
      console.error('❌ Invalid test_id:', test);
      return '/participant/tests'; // Fallback to tests list
    }
    if (!test.submission_id || isNaN(test.submission_id)) {
      console.error('❌ Invalid submission_id:', test);
      return '/participant/tests'; // Fallback to tests list
    }

    const href = isQuiz
      ? `/participant/tests/take/mcq/${test.test_id}?submission=${test.submission_id}`
      : `/participant/tests/take/interview/${test.test_id}?submission=${test.submission_id}`;

    console.log('✅ Generated href:', href, 'for test:', test.test_name, 'test_id:', test.test_id, 'submission_id:', test.submission_id);

    return href;
  };

  const defaultTab = upcomingTests.length > 0 ? 'upcoming' : 'completed';

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Participant workspace</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline" />
            <span className="text-slate-400">Tests</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">My Tests</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Access every assessment you&apos;re assigned, see due dates, and pick up where you left off.
          </p>
        </div>
        <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
          Participant
        </Badge>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Assigned</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-slate-900">{stats.assigned}</span>
            <CalendarClock className="size-6 text-slate-300" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">In Progress</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-slate-900">{stats.inProgress}</span>
            <Clock4 className="size-6 text-slate-300" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Completed</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-slate-900">{stats.completed}</span>
            <CheckCircle2 className="size-6 text-slate-300" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Average Score</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-slate-900">
              {stats.avgScore !== undefined ? `${stats.avgScore}%` : '—'}
            </span>
            <TrendingUp className="size-6 text-slate-300" />
          </CardContent>
        </Card>
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
          Loading tests…
        </div>
      ) : tests.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
            <div className="rounded-full bg-slate-100 p-3">
              <Play className="size-6 text-slate-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">No tests assigned</h3>
              <p className="text-sm text-slate-500">
                When your trainer assigns a test, it will appear here.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue={defaultTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 gap-2 rounded-full bg-slate-100 p-1 text-sm">
            <TabsTrigger value="upcoming" className="rounded-full">
              Upcoming ({upcomingTests.length})
            </TabsTrigger>
            <TabsTrigger value="completed" className="rounded-full">
              Completed ({completedTests.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="upcoming" className="focus-visible:outline-none">
            {upcomingTests.length ? (
              <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
                <CardHeader>
                  <CardTitle>Upcoming Tests</CardTitle>
                  <CardDescription>Tests you can start or continue</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Test</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Due</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {upcomingTests.map((test) => {
                        const isQuiz = test.test_type === TestType.QUIZ || (test.test_type as string) === 'MCQ';
                        const friendlyType = isQuiz ? 'Quiz' : 'Interview';
                        const { formatted: dueDate, status: dueStatus } = formatDueDate(test.due_date);
                        const href = getActionHref(test, isQuiz);
                        const scoreLabel =
                          test.final_score != null ? `${Math.round(test.final_score)}%` : '—';

                        return (
                          <TableRow key={test.submission_id}>
                            <TableCell className="font-medium text-slate-900">{test.test_name}</TableCell>
                            <TableCell>
                              <Badge variant={isQuiz ? 'default' : 'secondary'}>{friendlyType}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  test.status === SubmissionStatus.IN_PROGRESS
                                    ? 'outline'
                                    : test.status === SubmissionStatus.ABANDONED
                                      ? 'destructive'
                                      : 'default'
                                }
                              >
                                {statusLabels[test.status]}
                              </Badge>
                            </TableCell>
                            <TableCell>{dueDate}</TableCell>
                            <TableCell>{scoreLabel}</TableCell>
                            <TableCell className="text-right">
                              <Button size="sm" asChild>
                                <Link href={href}>{renderActionLabel(test.status, isQuiz)}</Link>
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                  <div className="rounded-full bg-slate-100 p-3">
                    <Play className="size-6 text-slate-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">No upcoming tests</h3>
                    <p className="text-sm text-slate-500">Stay tuned—new assignments will appear here.</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
          <TabsContent value="completed" className="focus-visible:outline-none">
            {completedTests.length ? (
              <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
                <CardHeader>
                  <CardTitle>Completed Tests</CardTitle>
                  <CardDescription>Review your completed work and insights</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Test</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Completed</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Details</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {completedTests.map((test) => {
                        const isQuiz = test.test_type === TestType.QUIZ || (test.test_type as string) === 'MCQ';
                        const friendlyType = isQuiz ? 'Quiz' : 'Interview';
                        const completedAt = formatTableDate(test.submitted_at);
                        const scoreLabel =
                          test.final_score != null ? `${Math.round(test.final_score)}%` : '—';
                        const statusVariant =
                          test.status === SubmissionStatus.ABANDONED ? 'destructive' : 'secondary';

                        return (
                          <TableRow
                            key={test.submission_id}
                            className="cursor-pointer transition-colors hover:bg-slate-50"
                            onClick={() => handleOpenDetails(test)}
                          >
                            <TableCell className="font-medium text-slate-900">{test.test_name}</TableCell>
                            <TableCell>
                              <Badge variant={isQuiz ? 'default' : 'secondary'}>{friendlyType}</Badge>
                            </TableCell>
                            <TableCell>{completedAt}</TableCell>
                            <TableCell>{scoreLabel}</TableCell>
                            <TableCell>
                              <Badge variant={statusVariant}>{statusLabels[test.status]}</Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleOpenDetails(test);
                                }}
                              >
                                <Eye className="mr-2 size-4" />
                                View
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                  <div className="rounded-full bg-slate-100 p-3">
                    <CheckCircle2 className="size-6 text-slate-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">No completed tests yet</h3>
                    <p className="text-sm text-slate-500">Once you finish a test, it will appear here.</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      )}
      <ParticipantTestDetailsSheet test={selectedTest} open={detailsOpen} onOpenChange={handleDetailsToggle} />

    </div>
  );
}
