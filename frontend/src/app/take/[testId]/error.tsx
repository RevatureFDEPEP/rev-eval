'use client';

import { Button } from '@/components/ui/button';

/**
 * Error boundary for /take/[testId] — covers a failed session mint (empty
 * question bank, question-management-service unavailable, unexpected gateway
 * errors). `reset()` re-runs the server component to retry minting.
 */
export default function TakeError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6 text-center">
      <h2 className="text-lg font-semibold">Couldn’t start the test</h2>
      <p className="text-sm text-muted-foreground">
        Something went wrong setting up your session. Please try again in a moment.
      </p>
      <Button onClick={reset}>Retry</Button>
    </div>
  );
}
