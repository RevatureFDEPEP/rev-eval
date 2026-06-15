/**
 * Filter bar (children slot) for /admin/dashboard.
 *
 * Server component: fetches the trainer's tests to populate the selector, then
 * renders the URL-synced <DashboardFilters>. The explicit TRAINER re-check here
 * satisfies the spec's "even if middleware was bypassed" guard (the layout
 * gates first, so this is belt-and-suspenders).
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getTrainerTestsServer } from '@/lib/api/server';
import { DashboardFilters } from '@/components/admin/DashboardFilters';

export default async function AdminDashboardFilters() {
  const session = await getSession();
  if (!session || session.role.toUpperCase() !== 'TRAINER') {
    redirect('/unauthorized');
  }

  const tests = await getTrainerTestsServer();

  return <DashboardFilters tests={tests.map((t) => ({ id: t.id, name: t.name }))} />;
}
