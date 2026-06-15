/**
 * Error boundary for the pass-rate panel (@passrate slot). A reporting-service
 * failure (incl. a 403) blanks only this panel; filters + sibling chart stay up.
 */
'use client';

import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';

export default function PassRateError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SectionErrorFallback
      title="Couldn't load pass rates"
      description="The pass-rate report is temporarily unavailable. The rest of the dashboard is unaffected."
      error={error}
      reset={reset}
    />
  );
}
