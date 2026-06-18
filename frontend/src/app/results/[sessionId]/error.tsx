'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

/**
 * Route-level error boundary — the outer safety net for the results segment.
 * Individual data regions have their own boundaries (SectionErrorBoundary);
 * this catches anything that escapes them (e.g. a failure rendering the page
 * chrome itself) and offers a full retry.
 */
export default function ResultsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Results page error:', error);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-6xl items-center justify-center p-4 sm:p-6 lg:p-8">
      <Card className="w-full max-w-md border-red-200 bg-red-50">
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          <AlertTriangle className="h-8 w-8 text-red-500" aria-hidden="true" />
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-red-900">
              We couldn&apos;t load your results
            </h2>
            <p className="text-sm text-red-700">
              Something went wrong fetching your report. Please try again.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={reset}
            className="border-red-300 text-red-700 hover:bg-red-100"
          >
            <RotateCw className="mr-2 h-4 w-4" aria-hidden="true" />
            Try again
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
