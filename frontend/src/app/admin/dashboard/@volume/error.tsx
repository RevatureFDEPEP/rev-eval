/**
 * Error boundary for the attempt-volume panel (@volume slot). A failure here
 * (incl. a 403) blanks only this panel; filters + sibling chart stay up.
 */
'use client';

import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';

export default function VolumeError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SectionErrorFallback
      title="Couldn't load attempt volume"
      description="The attempt-volume chart is temporarily unavailable. The rest of the dashboard is unaffected."
      error={error}
      reset={reset}
    />
  );
}
