'use client';

import { useRouter } from 'next/navigation';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface SectionErrorFallbackProps {
  /** Human label for the panel that failed, e.g. "summary" or "attempts". */
  title: string;
  /**
   * Retry handler. Defaults to router.refresh(), which re-runs the server
   * component (and its data fetch) for the current route — the right reset
   * when the failure came from a server-side fetch. The error boundary passes
   * its own reset() for client-render failures.
   */
  onRetry?: () => void;
}

/**
 * Inline fallback for a single failed results region. Rendered both by a
 * region's own try/catch (server-fetch failure) and by SectionErrorBoundary
 * (client-render failure), so a single panel can fail and recover on its own
 * without blanking the rest of the page.
 */
export function SectionErrorFallback({ title, onRetry }: SectionErrorFallbackProps) {
  const router = useRouter();
  const handleRetry = onRetry ?? (() => router.refresh());

  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
        <AlertTriangle className="h-6 w-6 text-red-500" aria-hidden="true" />
        <p className="text-sm text-red-800">
          We couldn&apos;t load the {title} right now.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleRetry}
          className="border-red-300 text-red-700 hover:bg-red-100"
        >
          <RotateCw className="mr-2 h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
      </CardContent>
    </Card>
  );
}
