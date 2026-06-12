/**
 * Panel-scoped error fallback shared by the /results/[sessionId] section
 * boundaries (W4-F2). Each parallel-route slot's error.tsx renders this, so a
 * 500 from the reporting service blanks only its own panel — the page chrome
 * and sibling sections stay interactive.
 */
'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SectionErrorFallbackProps {
  title: string;
  description: string;
  error: Error & { digest?: string };
  reset: () => void;
}

export function SectionErrorFallback({
  title,
  description,
  error,
  reset,
}: SectionErrorFallbackProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const retry = () => {
    // reset() alone re-renders the boundary with the cached server payload;
    // router.refresh() re-runs the slot's server component for fresh data.
    startTransition(() => {
      router.refresh();
      reset();
    });
  };

  return (
    <Card data-testid="results-section-error">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>{description}</p>
        {error.digest && (
          <p className="text-xs text-muted-foreground/70">Reference: {error.digest}</p>
        )}
        <Button onClick={retry} disabled={isPending}>
          {isPending ? 'Retrying…' : 'Retry'}
        </Button>
      </CardContent>
    </Card>
  );
}
