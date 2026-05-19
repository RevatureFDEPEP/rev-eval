'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import type { TestSubmission } from '@/lib/api/types';
import { Calendar, Clock, User, FileText } from 'lucide-react';
import { formatTableDate } from '@/lib/utils/date';

interface BasicSubmissionSheetProps {
  submission: TestSubmission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BasicSubmissionSheet({
  submission,
  open,
  onOpenChange,
}: BasicSubmissionSheetProps) {
  if (!submission) return null;

  const isAssigned = submission.status === 'ASSIGNED';
  const isInProgress = submission.status === 'IN_PROGRESS';

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[600px] lg:max-w-[700px]"
      >
        <SheetTitle className="sr-only">Submission #{submission.id}</SheetTitle>
        <div className="flex w-full flex-col gap-6 px-4 sm:px-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Submission #{submission.id}</Badge>
                <Badge variant="outline">Test ID: {submission.test_id}</Badge>
                <Badge variant={isAssigned ? 'outline' : 'default'}>
                  {submission.status}
                </Badge>
                {submission.test?.test_type && (
                  <Badge variant="secondary" className="capitalize">
                    {submission.test.test_type.toLowerCase()}
                  </Badge>
                )}
              </div>
              <h2 className="text-3xl font-semibold text-slate-900">
                {submission.test?.name || `Test #${submission.test_id}`}
              </h2>
              <p className="max-w-2xl text-sm text-slate-500">
                {isAssigned
                  ? 'This test has been assigned but not started yet.'
                  : 'This test is currently in progress.'}
              </p>
            </div>
          </header>

          <div className="space-y-4">
            {/* Participant Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-slate-600" />
                  Participant Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Name:</span>
                  <span className="text-slate-900 font-medium">
                    {submission.participant_name || `User #${submission.user_id}`}
                  </span>
                </div>
                {submission.participant_email && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Email:</span>
                    <span className="text-slate-900">{submission.participant_email}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">User ID:</span>
                  <span className="text-slate-900 font-mono">#{submission.user_id}</span>
                </div>
              </CardContent>
            </Card>

            {/* Test Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-slate-600" />
                  Test Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {submission.test?.test_type && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Test Type:</span>
                    <Badge variant="outline" className="capitalize">
                      {submission.test.test_type.toLowerCase()}
                    </Badge>
                  </div>
                )}
                {submission.test?.role && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Role:</span>
                    <span className="text-slate-900">{submission.test.role}</span>
                  </div>
                )}
                {submission.test?.curriculum && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Curriculum:</span>
                    <span className="text-slate-900">{submission.test.curriculum}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Timeline Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-slate-600" />
                  Timeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Assigned At:</span>
                  <span className="text-slate-900">{formatTableDate(submission.assigned_at)}</span>
                </div>
                {submission.due_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Due Date:</span>
                    <span className="text-slate-900 font-medium">{formatTableDate(submission.due_date)}</span>
                  </div>
                )}
                {submission.started_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Started At:</span>
                    <span className="text-slate-900">{formatTableDate(submission.started_at)}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Status Information */}
            <Card className={isAssigned ? 'border-slate-200 bg-slate-50' : 'border-blue-200 bg-blue-50'}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className={`h-5 w-5 ${isAssigned ? 'text-slate-600' : 'text-blue-600'}`} />
                  Current Status
                </CardTitle>
                <CardDescription>
                  {isAssigned
                    ? 'Waiting for participant to begin'
                    : 'Participant is actively working on this test'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">Status:</span>
                    <Badge variant={isAssigned ? 'outline' : 'default'} className="text-sm">
                      {submission.status}
                    </Badge>
                  </div>
                  {isInProgress && (
                    <div className="mt-3 text-sm text-slate-600">
                      <p>The participant has started the test and is currently working on it. Results and scores will be available once the test is completed.</p>
                    </div>
                  )}
                  {isAssigned && (
                    <div className="mt-3 text-sm text-slate-600">
                      <p>The test has been assigned but not yet started. The participant will need to navigate to their dashboard to begin.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* No Results Available Notice */}
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="rounded-full bg-amber-100 p-2">
                    <Clock className="h-5 w-5 text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-amber-900 mb-1">No Results Available Yet</h3>
                    <p className="text-sm text-amber-800">
                      Test results, scores, and detailed feedback will be available after the participant completes the test and it has been evaluated.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
