import { notFound, redirect } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { createQuizSessionServer, ServerApiError } from '@/lib/api/server';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { getSession } from '@/lib/session';
import { TestRunner } from '@/components/take/TestRunner';
import type { QuizSessionRead } from '@/lib/api/types';

type TakePageProps = {
  params: Promise<{ testId: string }>;
  searchParams: Promise<{ submission?: string | string[] }>;
};

function parsePositiveInt(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function firstSearchValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function SessionStartError({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">{message}</p>
          <Button asChild>
            <a href="/participant/tests">Back to tests</a>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}

function sessionErrorMessage(status: number): string {
  if (status === 409) return 'An active session already exists for this test.';
  if (status === 422) return 'This test does not have available questions yet.';
  if (status === 502) return 'The question service is unavailable.';
  return 'The quiz session could not be started.';
}

export default async function TakeTestPage({ params, searchParams }: TakePageProps) {
  const [{ testId }, query] = await Promise.all([params, searchParams]);
  const parsedTestId = parsePositiveInt(testId);
  if (parsedTestId === null) notFound();

  const rawSubmissionId = firstSearchValue(query.submission);
  let submissionId: number | undefined;
  if (rawSubmissionId !== undefined) {
    const parsedSubmissionId = parsePositiveInt(rawSubmissionId);
    if (parsedSubmissionId === null) notFound();
    submissionId = parsedSubmissionId;
  }

  const session = await getSession();
  if (!session) redirect('/');

  let quizSession: QuizSessionRead;
  try {
    quizSession = await createQuizSessionServer({
      testId: parsedTestId,
      ...(submissionId !== undefined ? { submissionId } : {}),
    });
  } catch (error) {
    if (error instanceof ServerApiError) {
      if (error.status === 401) redirect('/');
      if (error.status === 404) notFound();
      return (
        <SessionStartError
          title="Unable to start quiz"
          message={sessionErrorMessage(error.status)}
        />
      );
    }
    throw error;
  }

  const clientSession = {
    session_id: quizSession.session_id,
    test_id: quizSession.test_id,
    user_id: quizSession.user_id,
    status: quizSession.status,
    current_index: quizSession.current_index,
    server_now: quizSession.server_now,
    expires_at: quizSession.expires_at,
    first_question: quizSession.first_question,
    questions: quizSession.questions,
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6">
      <AuthProvider
        identity={{
          userId: session.userId,
          email: session.email,
          role: session.role,
        }}
      >
        <TestRunner session={clientSession} />
      </AuthProvider>
    </main>
  );
}
