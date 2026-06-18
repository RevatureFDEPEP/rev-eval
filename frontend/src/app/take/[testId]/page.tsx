import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { TmsSessionStartResponse } from '@/lib/api/types';
import { TestRunner } from './TestRunner';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL ?? 'http://api-gateway:8000';

interface TakeTestPageProps {
  params: Promise<{ testId: string }>;
}

export default async function TakeTestPage({ params }: TakeTestPageProps) {
  const { testId } = await params;
  const testIdNum = parseInt(testId, 10);

  if (isNaN(testIdNum)) {
    redirect('/participant/tests');
  }

  const jar = await cookies();
  // pep_session takes priority; fall back to the standard auth_token cookie.
  const token = jar.get('pep_session')?.value ?? jar.get('auth_token')?.value;

  if (!token) {
    redirect('/');
  }

  let session: TmsSessionStartResponse;
  try {
    const res = await fetch(`${API_GATEWAY_URL}/v1/api/sessions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ test_id: testIdNum }),
      cache: 'no-store',
    });

    if (!res.ok) {
      redirect('/participant/tests');
    }

    session = (await res.json()) as TmsSessionStartResponse;
  } catch {
    redirect('/participant/tests');
  }

  return <TestRunner session={session} />;
}
