/**
 * Error boundary for the summary headline region (children slot).
 * A reporting-service failure here blanks only the summary panel.
 */
'use client';

import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';

export default function SummaryError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SectionErrorFallback
      title="Couldn't load your summary"
      description="The results summary is temporarily unavailable. Your attempt history and chart may still load below."
      error={error}
      reset={reset}
    />
  );
}
