"use client";

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AssignTestModal } from '@/components/trainer/AssignTestModal';
import type { TrainerTestInfo } from '@/lib/api/types';
import { formatTableDate } from '@/lib/utils/date';
import {
  CheckCircle2,
  Clock,
  Copy,
  Edit,
  Layers,
  Trash2,
  Users,
} from 'lucide-react';

interface TestDetailsSheetProps {
  test: TrainerTestInfo | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tests: TrainerTestInfo[];
  onAssignSuccess?: () => void;
  currentUserId?: number | null;
}

export function TestDetailsSheet({
  test,
  open,
  onOpenChange,
  tests,
  onAssignSuccess,
  currentUserId = null,
}: TestDetailsSheetProps) {
  const router = useRouter();
  const availableTests = useMemo(() => (test ? [test] : tests), [test, tests]);

  if (!test) return null;

  const isQuiz = (test.test_type as string) === 'QUIZ' || (test.test_type as string) === 'MCQ';
  const testType = isQuiz ? 'Quiz' : 'Interview';
  const cloneTypeParam = isQuiz ? 'QUIZ' : 'INTERVIEW';
  const durationMinutes = test.duration_seconds ? Math.round(test.duration_seconds / 60) : null;
  const skillCount = test.skills?.length ?? 0;
  const hasSkills = skillCount > 0;
  const canEdit = test.created_by_id != null && currentUserId != null && Number(test.created_by_id) === Number(currentUserId);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[70vw]"
      >
        <SheetTitle className="sr-only">Test Details: {test.name}</SheetTitle>
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 sm:px-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={isQuiz ? 'default' : 'secondary'}>{testType}</Badge>
                <Badge variant={test.active ? 'default' : 'outline'}>
                  {test.active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <h2 className="text-3xl font-semibold text-slate-900">{test.name}</h2>
              <p className="max-w-2xl text-sm text-slate-500">
                Review configuration, track submissions, and manage upcoming enhancements for this assessment.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200/70 bg-white/90 p-3 shadow-sm">
              {canEdit && (
                <Button
                  className="transition-transform hover:-translate-y-0.5"
                  onClick={() => {
                    onOpenChange(false);
                    router.push(`/trainer/tests/edit/${test.id}`);
                  }}
                >
                  <Edit className="mr-2 size-4" />
                  Edit Test
                </Button>
              )}
              <Button
                variant="outline"
                className="transition-transform hover:-translate-y-0.5"
                onClick={() => {
                  onOpenChange(false);
                  router.push(`/trainer/tests/create?type=${cloneTypeParam}&clone=${test.id}`);
                }}
              >
                <Copy className="mr-2 size-4" />
                Clone Test
              </Button>
              <Button variant="destructive" className="transition-transform hover:-translate-y-0.5">
                <Trash2 className="mr-2 size-4" />
                Archive / Delete
              </Button>
            </div>
          </header>

          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-2 gap-2 rounded-full bg-muted/70 p-1 text-sm md:grid-cols-5">
              <TabsTrigger
                value="overview"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="submissions"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Submissions
              </TabsTrigger>
              <TabsTrigger
                value="analytics"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Analytics
              </TabsTrigger>
              <TabsTrigger
                value="skills"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Skills
              </TabsTrigger>
              <TabsTrigger
                value="questions"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Questions
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-5">
              <section className="grid gap-4 md:grid-cols-2">
                <Card className="border border-orange-100/80 shadow-sm">
                  <CardHeader>
                    <CardTitle>Assessment Overview</CardTitle>
                    <CardDescription>Key configuration details</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-500">Type</span>
                      <span className="font-medium text-slate-900">{testType}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-500">Status</span>
                      <span className="font-medium text-slate-900">{test.active ? 'Active' : 'Inactive'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-500">Duration</span>
                      <span className="font-medium text-slate-900">
                        {durationMinutes ? `${durationMinutes} minutes` : 'No time limit'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-500">Created on</span>
                      <span className="font-medium text-slate-900">
                        {formatTableDate(test.created_at)}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border border-purple-100/80 shadow-sm">
                  <CardHeader>
                    <CardTitle>Assignment Snapshot</CardTitle>
                    <CardDescription>Participation at a glance</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-4 sm:grid-cols-3">
                    <div className="flex flex-col items-center justify-center rounded-xl border border-orange-100/70 bg-gradient-to-b from-white to-orange-50/70 p-4">
                      <Users className="mb-2 size-5 text-orange-400" />
                      <p className="text-xl font-semibold text-slate-900">{test.total_submissions}</p>
                      <p className="mt-1 text-xs font-medium text-slate-500">Assigned</p>
                    </div>
                    <div className="flex flex-col items-center justify-center rounded-xl border border-purple-100/70 bg-gradient-to-b from-white to-purple-50/70 p-4">
                      <CheckCircle2 className="mb-2 size-5 text-purple-400" />
                      <p className="text-xl font-semibold text-slate-900">{test.completed_submissions}</p>
                      <p className="mt-1 text-xs font-medium text-slate-500">Completed</p>
                    </div>
                    <div className="flex flex-col items-center justify-center rounded-xl border border-purple-100/70 bg-gradient-to-b from-white to-purple-50/40 p-4">
                      <Clock className="mb-2 size-5 text-slate-500" />
                      <p className="text-xl font-semibold text-slate-900">{test.pending_submissions}</p>
                      <p className="mt-1 text-xs font-medium text-slate-500">Pending</p>
                    </div>
                  </CardContent>
                </Card>
              </section>

              <section className="grid gap-4 md:grid-cols-2">
                <Card className="border border-orange-100/80 bg-white/95 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <Layers className="size-5 text-orange-400" />
                      <div>
                        <CardTitle>Skill Coverage</CardTitle>
                        <CardDescription>
                          {hasSkills ? `${skillCount} skill${skillCount === 1 ? '' : 's'} included` : 'No skills linked yet'}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {hasSkills ? (
                      <div className="flex flex-wrap gap-2">
                        {test.skills?.map((skill) => (
                          <Badge key={skill.id} variant="secondary" className="rounded-full px-3 py-1 text-xs">
                            {skill.name}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">
                        Add skills while creating the test to focus the assessment outcomes.
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card className="border-dashed border-purple-200/80 bg-white/90 shadow-none">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <Users className="size-5 text-purple-400" />
                      <div>
                        <CardTitle>Participant Management</CardTitle>
                        <CardDescription>Controls arriving next release</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm text-slate-600">
                    <p>Expect cohort filters, reminder scheduling, and late submission workflows.</p>
                    <p className="text-xs text-slate-500">
                      Integrations: calendar sync, notification hooks, and real-time progress monitoring.
                    </p>
                  </CardContent>
                </Card>
              </section>
            </TabsContent>

            <TabsContent value="submissions">
              <Card className="border border-purple-100/80 shadow-sm">
                <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle>Submissions</CardTitle>
                    <CardDescription>Assign or review participant progress</CardDescription>
                  </div>
                  <AssignTestModal
                    tests={availableTests}
                    defaultTestId={test.id}
                    onSuccess={onAssignSuccess}
                    triggerClassName="w-auto"
                    hideTestSelection={true}
                  />
                </CardHeader>
                <CardContent className="space-y-4 text-sm text-slate-600">
                  <p className="text-sm">Detailed submissions tooling is on the way.</p>
                  <ul className="list-disc space-y-1 pl-4 text-xs text-slate-500">
                    <li>Upcoming views: participant status, score summaries, and manual overrides.</li>
                    <li>Export options and filters will be added to streamline reporting.</li>
                  </ul>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analytics">
              <Card className="border-dashed border-purple-200/80 bg-white/90 shadow-none">
                <CardHeader>
                  <CardTitle>Analytics Dashboard</CardTitle>
                  <CardDescription>Insights coming soon</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-slate-600">
                  <p>Trend lines, cohort comparisons, and predictive insights will appear here.</p>
                  <p className="text-xs text-slate-500">We&apos;re planning score heatmaps, topic breakdowns, and benchmarking tools.</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="skills">
              <Card className="border border-purple-100/80 bg-white/95 shadow-sm">
                <CardHeader>
                  <CardTitle>Skills</CardTitle>
                  <CardDescription>
                    {hasSkills ? 'Linked competencies for this assessment' : 'No skills linked yet'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-slate-600">
                  {hasSkills ? (
                    test.skills?.map((skill) => (
                      <div key={skill.id} className="rounded-lg border border-slate-200 bg-white p-3">
                        <p className="text-sm font-medium text-slate-800">{skill.name}</p>
                        <p className="text-xs text-slate-500">
                          {skill.description ? skill.description : 'No description provided.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p>
                      Skills will appear here once they are associated with this test. Add them from the creation flow to tailor feedback.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="questions">
              <Card className="border-dashed border-purple-200/80 bg-white/90 shadow-none">
                <CardHeader>
                  <CardTitle>Question Builder</CardTitle>
                  <CardDescription>Content editing UI coming soon</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-slate-600">
                  <p>Future updates will let you edit question order, pool logic, and adaptive rules.</p>
                  <p className="text-xs text-slate-500">Roadmap: collaborative editing, review workflows, and version compare.</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  );
}
