/**
 * /results/[sessionId] — candidate results screen (W4-F2).
 *
 * Parallel-route layout: the three data regions (summary headline = children,
 * attempts table = @attempts, score chart = @chart) are independent slots,
 * each with its own loading.tsx (per-region Suspense skeleton) and error.tsx
 * (per-region boundary + retry). The chrome below renders on first byte while
 * the slots stream in; one failing reporting call blanks only its panel.
 *
 * Detail-view layout per spec: headline summary full-width, table + chart in
 * a responsive grid — single column on mobile, two columns on desktop.
 */
import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';

interface ResultsLayoutProps {
  children: ReactNode;
  attempts: ReactNode;
  chart: ReactNode;
}

export default async function ResultsLayout({ children, attempts, chart }: ResultsLayoutProps) {
  // Middleware already auth-gates /results/*; this mirrors the /take belt-and-
  // suspenders so a direct render without a session never hits the gateway.
  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Your results</h1>
        <p className="text-sm text-muted-foreground">
          Summary, attempt history, and score trend for {session.email}
        </p>
      </header>
      <section aria-label="Results summary">{children}</section>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section aria-label="Attempt history">{attempts}</section>
        <section aria-label="Score trend">{chart}</section>
      </div>
    </main>
  );
}
