/**
 * Error boundary for the attempts table region (@attempts slot).
 * A reporting-service failure here blanks only this panel.
 */
'use client';

import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';

export default function AttemptsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SectionErrorFallback
      title="Couldn't load your attempt history"
      description="The attempt list is temporarily unavailable. The rest of the page is unaffected."
      error={error}
      reset={reset}
    />
  );
}
