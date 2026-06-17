'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ResultsError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('Results page error:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <h2 className="text-xl font-semibold text-slate-900">Failed to load results</h2>
      <p className="text-sm text-slate-500 max-w-sm">
        {error.message || 'Something went wrong fetching your results.'}
      </p>
      <div className="flex gap-3">
        <Button onClick={reset} variant="default">Try again</Button>
        <Button asChild variant="outline">
          <Link href="/participant/tests">Back to Tests</Link>
        </Button>
      </div>
    </div>
  );
}
