import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { getSession } from '@/lib/session';

export default async function TrainerLayout({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session || !['TRAINER', 'ADMIN'].includes(session.role.toUpperCase())) {
    redirect('/unauthorized');
  }
  return <>{children}</>;
}
