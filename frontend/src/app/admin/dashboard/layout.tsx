import type { ReactNode } from 'react';
import { DashboardShell } from '@/components/layout/dashboard-shell';

/**
 * /admin/dashboard chrome. The route lives outside the (dashboard) group (which
 * is trainer/participant-scoped) but reuses DashboardShell for the sidebar +
 * signed-in guard. The authoritative TRAINER role gate is server-side: the
 * Edge middleware (resolveAccess) plus the explicit check in page.tsx.
 */
export default function AdminDashboardLayout({ children }: { children: ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>;
}
