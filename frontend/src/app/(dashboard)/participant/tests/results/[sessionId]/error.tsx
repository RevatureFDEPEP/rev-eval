'use client';

/**
 * Route-level error boundary for the quiz results page. Catches unexpected
 * render/data errors and offers a retry without dumping a stack to the user.
 */
import { useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

export default function ResultsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Quiz results page error:', error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-3xl items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-4 pt-6 text-center">
          <AlertTriangle className="size-12 text-amber-600" />
          <h2 className="text-lg font-semibold">Something went wrong</h2>
          <p className="text-sm text-slate-600">
            We couldn&apos;t display your quiz result. Please try again.
          </p>
          <div className="flex gap-3">
            <Button onClick={reset}>Try again</Button>
            <Button variant="outline" asChild>
              <Link href="/participant/tests">Back to Tests</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
