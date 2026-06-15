/**
 * /admin/dashboard — trainer aggregate reporting (W4-F4).
 *
 * Server component. Second-layer RBAC: even though the Edge middleware already
 * gates /admin to TRAINER, this re-checks the verified session role and
 * redirects a non-trainer who somehow bypassed it — defense in depth, the
 * server gate is never the client's responsibility.
 *
 * Filter controls + charts are wired in M4; this commit establishes the route
 * and its guard.
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';

export default async function AdminDashboardPage() {
  const session = await getSession();
  if (!session || session.role.toUpperCase() !== 'TRAINER') {
    redirect('/unauthorized');
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Trainer dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Aggregate reporting across tests and candidates.
        </p>
      </header>
    </main>
  );
}
