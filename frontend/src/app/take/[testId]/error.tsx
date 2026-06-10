/**
 * Route-level error boundary for /take/[testId] (W3-F7 item 5).
 *
 * Catches session-mint failures that aren't a 404 — an empty question bank
 * (422) or question-management-service being down (502) — and shows a
 * recoverable message instead of the raw Next.js 500 page. `reset()`
 * re-renders the server component, which re-attempts the mint (idempotent:
 * an existing ACTIVE session is reused, not duplicated).
 */
'use client';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function TakeError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl p-6" data-testid="take-error">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            We couldn&apos;t start your test
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600">
          <p>
            Something went wrong while setting up your session. Try again — if
            the problem persists, contact your trainer.
          </p>
          {error.digest && (
            <p className="text-xs text-slate-400">Reference: {error.digest}</p>
          )}
          <Button onClick={reset}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}
