'use client';

import { use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { InterviewInterface } from '@/components/interview/InterviewInterface';
import { useEffect, useState } from 'react';
import { getTest } from '@/lib/api';
import type { Test } from '@/lib/api/types';

interface InterviewTestPageProps {
  params: Promise<{
    testId: string;
  }>;
}

export default function InterviewTestPage({ params }: InterviewTestPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resolvedParams = use(params);

  const testId = parseInt(resolvedParams.testId, 10);
  const submissionId = parseInt(searchParams.get('submission') || '', 10);

  const [test, setTest] = useState<Test | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Validate testId
  if (isNaN(testId)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Invalid Test ID</h2>
                <p className="mt-2 text-sm text-slate-600">
                  The test ID in the URL is invalid. Received: "{resolvedParams.testId}"
                </p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Validate submissionId
  if (isNaN(submissionId)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Invalid Submission ID</h2>
                <p className="mt-2 text-sm text-slate-600">
                  Missing or invalid submission ID in URL.
                </p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Load test data
  useEffect(() => {
    const loadTest = async () => {
      try {
        setIsLoading(true);
        const testData = await getTest(testId);
        setTest(testData);
      } catch (err) {
        console.error('Failed to load test:', err);
        setError(err instanceof Error ? err.message : 'Failed to load test data');
      } finally {
        setIsLoading(false);
      }
    };

    loadTest();
  }, [testId]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <div className="size-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
              <p className="text-center text-sm text-slate-600">Loading interview...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show error state
  if (error || !test) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="size-12 text-red-600" />
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-900">Error Loading Interview</h2>
                <p className="mt-2 text-sm text-slate-600">{error || 'Test not found'}</p>
              </div>
              <Button onClick={() => router.push('/participant/tests')}>Back to Tests</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Assessment</p>
            <h1 className="text-3xl font-semibold text-slate-900">Live Interview</h1>
            <p className="text-sm text-slate-500">AI-powered conversational assessment</p>
          </div>
          <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
            Participant
          </Badge>
        </div>
      </section>

      {/* Interview Interface */}
      <InterviewInterface
        testId={testId}
        testName={test.name}
        submissionId={submissionId}
      />
    </div>
  );
}
