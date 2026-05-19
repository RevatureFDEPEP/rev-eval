import { redirect } from 'next/navigation';
import { getSession, normalizeRole } from '@/lib/session';
import { LandingAuth } from './_components/landing-auth';

export default async function HomePage() {
  const session = await getSession();
  if (session) {
    const role = normalizeRole(session.role);
    redirect(role === 'trainer' || role === 'admin' ? '/trainer/dashboard' : '/participant/dashboard');
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100">
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <header className="mb-12 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Revature EvaluAI</h1>
        </header>
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <h2 className="text-4xl font-bold text-gray-900">AI-Powered Technical Assessments</h2>
            <p className="mt-4 text-lg text-gray-600">
              Streamline your evaluation process with intelligent test management,
              automated scoring, and comprehensive analytics for trainers and students.
            </p>
            <ul className="mt-6 space-y-2 text-sm text-gray-600">
              <li>• Create tests, bulk-assign to students</li>
              <li>• Take quizzes and live interviews</li>
              <li>• Trainer review with AI-assisted scoring</li>
            </ul>
          </div>
          <LandingAuth />
        </div>
      </div>
    </div>
  );
}
