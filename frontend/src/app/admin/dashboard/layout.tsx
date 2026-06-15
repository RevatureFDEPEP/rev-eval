/**
 * /admin/dashboard — trainer aggregate reporting (W4-F4).
 *
 * Parallel-route layout (mirrors the W4-F2 results page): the filter bar is the
 * children slot, and the two data regions — @passrate and @volume — are
 * independent slots, each with its own loading.tsx (Suspense skeleton) and
 * error.tsx (per-panel boundary + retry). One failing reporting call blanks
 * only its panel; the filters and sibling chart stay interactive.
 *
 * Authoritative server-side RBAC: the Edge middleware gates /admin to TRAINER,
 * and this layout re-checks the verified session role before any slot fetches,
 * redirecting a non-trainer who bypassed the middleware. /admin is TRAINER-only
 * to match the W4-F3 backend gate (ADMIN gets 403).
 */
import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { DashboardShell } from '@/components/layout/dashboard-shell';

interface AdminDashboardLayoutProps {
  children: ReactNode;
  passrate: ReactNode;
  volume: ReactNode;
}

export default async function AdminDashboardLayout({
  children,
  passrate,
  volume,
}: AdminDashboardLayoutProps) {
  const session = await getSession();
  if (!session || session.role.toUpperCase() !== 'TRAINER') {
    redirect('/unauthorized');
  }

  return (
    <DashboardShell>
      <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Trainer dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Aggregate reporting across tests and candidates.
          </p>
        </header>
        <section aria-label="Filters">{children}</section>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section aria-label="Pass rate per test">{passrate}</section>
          <section aria-label="Attempt volume over time">{volume}</section>
        </div>
      </main>
    </DashboardShell>
  );
}
