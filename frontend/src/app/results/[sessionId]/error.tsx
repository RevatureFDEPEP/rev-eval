'use client';

/**
 * Route-level error boundary (W4-F2, R3).
 *
 * Catches anything thrown outside the per-region boundaries (e.g. an unexpected
 * failure in the page shell). Per-region 500s are handled by RegionErrorBoundary
 * so they blank only their panel; this is the whole-page backstop with a retry.
 */
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

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
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="text-xl font-semibold text-slate-900">
          We couldn&apos;t load your results
        </h1>
        <p className="text-sm text-slate-600">
          Something went wrong fetching your results. Please try again in a moment.
        </p>
        <Button onClick={reset}>Try again</Button>
      </div>
    </main>
  );
}
