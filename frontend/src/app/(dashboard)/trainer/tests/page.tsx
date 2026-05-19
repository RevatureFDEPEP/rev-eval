'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@workos-inc/authkit-nextjs/components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TestDetailsSheet } from '@/components/trainer/TestDetailsSheet';
import { SubmissionReviewSheet } from '@/components/trainer/SubmissionReviewSheet';
import { QuizSubmissionSheet } from '@/components/trainer/QuizSubmissionSheet';
import { BasicSubmissionSheet } from '@/components/trainer/BasicSubmissionSheet';
import { getTrainerTests, getCurrentUser, getEvaluatedSubmissionsForTrainer, getGradedSubmissions, getAllSubmissionsForTrainer } from '@/lib/api';
import type { TrainerTestInfo, TestSubmission } from '@/lib/api/types';
import { Calendar, ClipboardCheck, ClipboardList, Layers, PlusCircle, Star } from 'lucide-react';
import { formatTableDate } from '@/lib/utils/date';

export default function TrainerTestsPage() {
  const { user, loading: authLoading } = useAuth({ ensureSignedIn: true });

  // Test Management state
  const [tests, setTests] = useState<TrainerTestInfo[]>([]);
  const [loadingTests, setLoadingTests] = useState(true);
  const [testsError, setTestsError] = useState<string | null>(null);
  const [selectedTest, setSelectedTest] = useState<TrainerTestInfo | null>(null);
  const [testSheetOpen, setTestSheetOpen] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);

  // Needs Review state (evaluated submissions)
  const [submissions, setSubmissions] = useState<TestSubmission[]>([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(true);
  const [submissionsError, setSubmissionsError] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<TestSubmission | null>(null);
  const [reviewSheetOpen, setReviewSheetOpen] = useState(false);
  const [quizSheetOpen, setQuizSheetOpen] = useState(false);
  const [basicSheetOpen, setBasicSheetOpen] = useState(false);

  // Graded submissions state
  const [gradedSubmissions, setGradedSubmissions] = useState<TestSubmission[]>([]);
  const [loadingGraded, setLoadingGraded] = useState(true);
  const [gradedError, setGradedError] = useState<string | null>(null);

  const loadTests = useCallback(async () => {
    try {
      setLoadingTests(true);
      setTestsError(null);
      const data = await getTrainerTests();
      setTests(data);
    } catch (err: unknown) {
      console.error('Tests error:', err);
      const message = err instanceof Error ? err.message : 'Unable to load tests';
      setTestsError(message);
    } finally {
      setLoadingTests(false);
    }
  }, []);

  const loadEvaluatedSubmissions = useCallback(async () => {
    try {
      setLoadingSubmissions(true);
      setSubmissionsError(null);
      const data = await getEvaluatedSubmissionsForTrainer();
      setSubmissions(data);
    } catch (err: unknown) {
      console.error('Submissions error:', err);
      const message = err instanceof Error ? err.message : 'Unable to load submissions';
      setSubmissionsError(message);
    } finally {
      setLoadingSubmissions(false);
    }
  }, []);

  const loadGradedSubmissions = useCallback(async () => {
    try {
      setLoadingGraded(true);
      setGradedError(null);
      const data = await getAllSubmissionsForTrainer();
      setGradedSubmissions(data);
    } catch (err: unknown) {
      console.error('All submissions error:', err);
      const message = err instanceof Error ? err.message : 'Unable to load submissions';
      setGradedError(message);
    } finally {
      setLoadingGraded(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    let cancelled = false;

    const loadUser = async () => {
      try {
        setLoadingUser(true);
        const profile = await getCurrentUser();
        if (!cancelled) {
          setCurrentUserId(profile.id);
        }
      } catch (err) {
        console.error('Failed to load current user profile:', err);
        if (!cancelled) {
          setCurrentUserId(null);
        }
      } finally {
        if (!cancelled) {
          setLoadingUser(false);
        }
      }
    };

    loadUser();
    loadTests();
    loadEvaluatedSubmissions();
    loadGradedSubmissions();

    return () => {
      cancelled = true;
    };
  }, [authLoading, user, loadTests, loadEvaluatedSubmissions, loadGradedSubmissions]);

  const testStats = useMemo(() => {
    const active = tests.filter((test) => test.active).length;
    const total = tests.length;
    const avgCompletion = tests.length
      ? Math.round(
          tests.reduce((acc, test) => acc + (test.completed_submissions || 0), 0) /
            Math.max(1, tests.reduce((acc, test) => acc + test.total_submissions, 0)) *
            100,
        )
      : 0;

    return { active, total, avgCompletion: Number.isFinite(avgCompletion) ? avgCompletion : 0 };
  }, [tests]);

  const gradingStats = useMemo(() => {
    const pendingReviews = submissions.length;
    const avgAIScore = submissions.length > 0
      ? Math.round(submissions.reduce((sum, sub) => sum + (sub.ai_score || 0), 0) / submissions.length)
      : 0;
    return { pendingReviews, avgAIScore };
  }, [submissions]);

  const handleTestClick = (test: TrainerTestInfo) => {
    setSelectedTest(test);
    setTestSheetOpen(true);
  };

  const handleTestSheetClose = () => {
    setTestSheetOpen(false);
    setSelectedTest(null);
  };

  const handleSubmissionClick = (submission: TestSubmission) => {
    const testType = submission.test?.test_type;
    const status = submission.status;

    // Handle ASSIGNED and IN_PROGRESS statuses (for both quiz and interview)
    if (status === 'ASSIGNED' || status === 'IN_PROGRESS') {
      setSelectedSubmission(submission);
      setBasicSheetOpen(true);
      return;
    }

    // Route based on test type and status
    if (testType === 'QUIZ') {
      // For quizzes, open QuizSubmissionSheet for completed/graded
      if (status === 'COMPLETED' || status === 'GRADED') {
        setSelectedSubmission(submission);
        setQuizSheetOpen(true);
      } else {
        // Fallback for other statuses
        setSelectedSubmission(submission);
        setQuizSheetOpen(true);
      }
      return;
    }

    if (testType === 'INTERVIEW') {
      if (status === 'GRADED' || status === 'EVALUATED') {
        // Open review sheet (read-only for GRADED, editable for EVALUATED)
        setSelectedSubmission(submission);
        setReviewSheetOpen(true);
      } else if (status === 'COMPLETED') {
        alert('This interview is completed but not yet evaluated by AI. Evaluation is pending.');
      } else {
        // Other statuses (ABANDONED, etc.)
        setSelectedSubmission(submission);
        setReviewSheetOpen(true);
      }
    } else {
      // Unknown test type
      setSelectedSubmission(submission);
      setReviewSheetOpen(true);
    }
  };

  const handleReviewSheetClose = () => {
    setReviewSheetOpen(false);
    setSelectedSubmission(null);
  };

  const handleQuizSheetClose = () => {
    setQuizSheetOpen(false);
    setSelectedSubmission(null);
  };

  const handleBasicSheetClose = () => {
    setBasicSheetOpen(false);
    setSelectedSubmission(null);
  };

  const handleReviewSuccess = () => {
    loadEvaluatedSubmissions();
    loadGradedSubmissions();
    handleReviewSheetClose();
  };

  if (authLoading || loadingUser || !user) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-4 text-sm text-slate-600">Loading trainer tools…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Trainer workspace</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline" />
            <span className="text-slate-400">Tests</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">Test Management</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Create, assign, and review assessments for your cohorts. Grade evaluated interviews.
          </p>
        </div>
        <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
          Trainer
        </Badge>
      </section>

      <Tabs defaultValue="management" className="w-full">
        <TabsList className="grid w-full max-w-2xl grid-cols-3">
          <TabsTrigger value="management">Management</TabsTrigger>
          <TabsTrigger value="needs-review">
            Pending Review
            {gradingStats.pendingReviews > 0 && (
              <Badge variant="secondary" className="ml-2 rounded-full px-2 py-0 text-xs">
                {gradingStats.pendingReviews}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="all-tests">
            All Tests
            {gradedSubmissions.length > 0 && (
              <Badge variant="secondary" className="ml-2 rounded-full px-2 py-0 text-xs">
                {gradedSubmissions.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Test Management Tab */}
        <TabsContent value="management" className="space-y-6">
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="border border-orange-100/70 bg-white/95 shadow-sm">
              <CardContent className="flex items-center justify-between py-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Total Tests</p>
                  <p className="text-2xl font-semibold text-slate-900">{testStats.total}</p>
                </div>
                <Layers className="size-6 text-orange-400" />
              </CardContent>
            </Card>
            <Card className="border border-purple-100/70 bg-white/95 shadow-sm">
              <CardContent className="flex items-center justify-between py-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Active</p>
                  <p className="text-2xl font-semibold text-slate-900">{testStats.active}</p>
                </div>
                <ClipboardList className="size-6 text-purple-400" />
              </CardContent>
            </Card>
            <Card className="border border-purple-100/70 bg-white/95 shadow-sm sm:col-span-2 lg:col-span-2">
              <CardContent className="flex items-center justify-between py-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Avg. Completion</p>
                  <p className="text-2xl font-semibold text-slate-900">{testStats.avgCompletion || 0}%</p>
                </div>
                <Calendar className="size-6 text-purple-400" />
              </CardContent>
            </Card>
          </section>

          {testsError && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {testsError}. Please verify the backend services are running.
                </p>
              </CardContent>
            </Card>
          )}

          {loadingTests ? (
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm text-slate-500">
              Loading tests…
            </div>
          ) : tests.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <div className="rounded-full bg-slate-100 p-3">
                  <PlusCircle className="size-6 text-slate-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">No tests yet</h3>
                  <p className="text-sm text-slate-500">
                    Start by creating your first assessment to begin assigning tests to participants.
                  </p>
                </div>
                <Button asChild className="transition-transform hover:-translate-y-0.5">
                  <Link href="/trainer/tests/create?type=QUIZ">Create your first test</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
              <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <CardTitle>All Tests</CardTitle>
                  <CardDescription>Overview of every assessment you&apos;ve created</CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button className="transition-transform hover:-translate-y-0.5">
                      <PlusCircle className="mr-2 size-4" />
                      Create New Test
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuItem asChild>
                      <Link href="/trainer/tests/create?type=QUIZ">Create Quiz</Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href="/trainer/tests/create?type=INTERVIEW">Create Interview</Link>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Assigned</TableHead>
                      <TableHead>Completed</TableHead>
                      <TableHead>Pending</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tests.map((test) => {
                      const isQuiz = (test.test_type as string) === 'QUIZ' || (test.test_type as string) === 'MCQ';
                      const friendlyType = isQuiz ? 'Quiz' : 'Interview';
                      const created = formatTableDate(test.created_at);
                      const duration = test.duration_seconds
                        ? `${Math.round(test.duration_seconds / 60)} mins`
                        : 'No limit';

                      return (
                        <TableRow
                          key={test.id}
                          className="cursor-pointer transition-all duration-200 hover:-translate-y-[1px] hover:bg-orange-50/60"
                          onClick={() => handleTestClick(test)}
                        >
                          <TableCell className="font-medium text-slate-900">{test.name}</TableCell>
                          <TableCell>
                            <Badge variant={isQuiz ? 'default' : 'secondary'}>{friendlyType}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={test.active ? 'default' : 'outline'}>
                              {test.active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell>{test.total_submissions}</TableCell>
                          <TableCell>{test.completed_submissions}</TableCell>
                          <TableCell>{test.pending_submissions}</TableCell>
                          <TableCell>{created}</TableCell>
                          <TableCell className="text-right text-slate-500">{duration}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                  <TableCaption>Includes both active and archived tests.</TableCaption>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Grading Tab */}
        {/* Needs Review Tab */}
        <TabsContent value="needs-review" className="space-y-6">
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card className="border border-purple-100/70 bg-white/95 shadow-sm">
              <CardContent className="flex items-center justify-between py-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Pending Reviews</p>
                  <p className="text-2xl font-semibold text-slate-900">{gradingStats.pendingReviews}</p>
                </div>
                <ClipboardCheck className="size-6 text-purple-400" />
              </CardContent>
            </Card>
            <Card className="border border-orange-100/70 bg-white/95 shadow-sm">
              <CardContent className="flex items-center justify-between py-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Avg AI Score</p>
                  <p className="text-2xl font-semibold text-slate-900">{gradingStats.avgAIScore}</p>
                </div>
                <Star className="size-6 text-orange-400" />
              </CardContent>
            </Card>
          </section>

          {submissionsError && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {submissionsError}. Please verify the backend services are running.
                </p>
              </CardContent>
            </Card>
          )}

          {loadingSubmissions ? (
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm text-slate-500">
              Loading submissions…
            </div>
          ) : submissions.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <div className="rounded-full bg-slate-100 p-3">
                  <ClipboardCheck className="size-6 text-slate-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">No interviews to review</h3>
                  <p className="text-sm text-slate-500">
                    All interviews have been reviewed. Check back later for new submissions.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
              <CardHeader>
                <CardTitle>Evaluated Interviews</CardTitle>
                <CardDescription>
                  Click on any row to review the transcript and provide your score
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Submission ID</TableHead>
                      <TableHead>Test ID</TableHead>
                      <TableHead>Participant</TableHead>
                      <TableHead>AI Score</TableHead>
                      <TableHead>Submitted</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {submissions.map((submission) => (
                      <TableRow
                        key={submission.id}
                        className="cursor-pointer transition-all duration-200 hover:-translate-y-[1px] hover:bg-purple-50/60"
                        onClick={() => handleSubmissionClick(submission)}
                      >
                        <TableCell className="font-medium text-slate-900">#{submission.id}</TableCell>
                        <TableCell>{submission.test_id}</TableCell>
                        <TableCell>{submission.participant_name || `User #${submission.user_id}`}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-mono">
                            {submission.ai_score || 'N/A'}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatTableDate(submission.submitted_at || '')}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{submission.status}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  <TableCaption>
                    Showing {submissions.length} interview{submissions.length !== 1 ? 's' : ''} awaiting
                    review
                  </TableCaption>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* All Tests Tab */}
        <TabsContent value="all-tests" className="space-y-6">
          {gradedError && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {gradedError}. Please verify the backend services are running.
                </p>
              </CardContent>
            </Card>
          )}

          {loadingGraded ? (
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm text-slate-500">
              Loading graded submissions…
            </div>
          ) : gradedSubmissions.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <div className="rounded-full bg-slate-100 p-3">
                  <ClipboardCheck className="size-6 text-slate-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">No graded submissions yet</h3>
                  <p className="text-sm text-slate-500">
                    Submissions you review will appear here after grading.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
              <CardHeader>
                <CardTitle>All Test Submissions</CardTitle>
                <CardDescription>
                  View all test submissions across all statuses (quizzes and interviews)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Submission ID</TableHead>
                      <TableHead>Test Name</TableHead>
                      <TableHead>Test Type</TableHead>
                      <TableHead>Participant</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Submitted</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gradedSubmissions.map((submission) => {
                      const isQuiz = submission.test?.test_type === 'QUIZ';
                      const isInterview = submission.test?.test_type === 'INTERVIEW';
                      const testName = submission.test?.name || `Test #${submission.test_id}`;
                      const testType = isQuiz ? 'Quiz' : isInterview ? 'Interview' : 'Unknown';

                      // Determine which score to display based on status
                      let scoreDisplay = 'N/A';
                      if (submission.final_score !== null && submission.final_score !== undefined) {
                        scoreDisplay = submission.final_score.toString();
                      } else if (submission.ai_score !== null && submission.ai_score !== undefined) {
                        scoreDisplay = submission.ai_score.toString();
                      }

                      // Status badge color based on status
                      const getStatusVariant = (status: string) => {
                        if (status === 'GRADED') return 'default';
                        if (status === 'EVALUATED') return 'secondary';
                        if (status === 'COMPLETED') return 'outline';
                        if (status === 'IN_PROGRESS') return 'secondary';
                        if (status === 'ASSIGNED') return 'outline';
                        return 'secondary';
                      };

                      return (
                        <TableRow
                          key={submission.id}
                          className="cursor-pointer transition-all duration-200 hover:-translate-y-[1px] hover:bg-green-50/60"
                          onClick={() => handleSubmissionClick(submission)}
                        >
                          <TableCell className="font-medium text-slate-900">#{submission.id}</TableCell>
                          <TableCell className="font-medium">{testName}</TableCell>
                          <TableCell>
                            <Badge variant={isQuiz ? 'outline' : 'secondary'}>
                              {testType}
                            </Badge>
                          </TableCell>
                          <TableCell>{submission.participant_name || `User #${submission.user_id}`}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono">
                              {scoreDisplay}
                            </Badge>
                          </TableCell>
                          <TableCell>{formatTableDate(submission.submitted_at || submission.assigned_at)}</TableCell>
                          <TableCell>
                            <Badge variant={getStatusVariant(submission.status)}>{submission.status}</Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                  <TableCaption>
                    Showing {gradedSubmissions.length} submission{gradedSubmissions.length !== 1 ? 's' : ''}
                  </TableCaption>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      <TestDetailsSheet
        test={selectedTest}
        open={testSheetOpen}
        onOpenChange={handleTestSheetClose}
        tests={tests}
        onAssignSuccess={loadTests}
        currentUserId={currentUserId}
      />

      <SubmissionReviewSheet
        submission={selectedSubmission}
        open={reviewSheetOpen}
        onOpenChange={handleReviewSheetClose}
        onReviewSuccess={handleReviewSuccess}
      />

      <QuizSubmissionSheet
        submission={selectedSubmission}
        open={quizSheetOpen}
        onOpenChange={handleQuizSheetClose}
      />

      <BasicSubmissionSheet
        submission={selectedSubmission}
        open={basicSheetOpen}
        onOpenChange={handleBasicSheetClose}
      />
    </div>
  );
}
