/**
 * Error boundary for the chart region (@chart slot).
 * A reporting-service failure here blanks only this panel.
 */
'use client';

import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';

export default function ChartError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SectionErrorFallback
      title="Couldn't load your score chart"
      description="The score trend chart is temporarily unavailable. The rest of the page is unaffected."
      error={error}
      reset={reset}
    />
  );
}
