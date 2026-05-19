import { redirect } from 'next/navigation';
import { getSession, normalizeRole } from '@/lib/session';

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  const role = normalizeRole(session.role);
  if (role === 'trainer' || role === 'admin') {
    redirect('/trainer/dashboard');
  }
  redirect('/participant/dashboard');
}
