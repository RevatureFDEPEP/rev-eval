import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import { getSession } from '@/lib/session';
import TestRunner from './TestRunner';
import type { SessionRead } from '@/lib/api/sessions';

const GATEWAY = process.env.API_GATEWAY_URL ?? 'http://api-gateway:8000';

interface TakePageProps {
  params: Promise<{ testId: string }>;
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <Card className="w-full max-w-md border-red-200">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4">
            <AlertCircle className="size-12 text-red-600" />
            <div className="text-center">
              <h2 className="text-lg font-semibold text-slate-900">Could Not Start Quiz</h2>
              <p className="mt-2 text-sm text-slate-600">{message}</p>
            </div>
            <Button variant="outline" asChild>
              <a href="/participant/tests">Back to Tests</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default async function TakePage({ params }: TakePageProps) {
  const { testId } = await params;

  const session = await getSession();
  if (!session) redirect('/');

  const testIdNum = Number(testId);
  if (!Number.isInteger(testIdNum) || testIdNum <= 0) {
    return <ErrorCard message={`Invalid test ID: "${testId}"`} />;
  }

  const jar = await cookies();
  const token = jar.get('auth_token')?.value ?? '';

  let quizSession: SessionRead | null = null;
  let sessionError: string | null = null;

  try {
    const res = await fetch(`${GATEWAY}/v1/api/sessions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ test_id: testIdNum }),
      cache: 'no-store',
    });

    if (!res.ok) {
      sessionError = await res.text().catch(() => String(res.status));
    } else {
      quizSession = (await res.json()) as SessionRead;
    }
  } catch (err) {
    sessionError = err instanceof Error ? err.message : 'Network error';
  }

  if (sessionError !== null || !quizSession) {
    return <ErrorCard message={sessionError ?? 'Session could not be created'} />;
  }

  const user = {
    id: session.userId,
    email: session.email,
    role: session.role,
  };

  return <TestRunner quizSession={quizSession} user={user} />;
}
