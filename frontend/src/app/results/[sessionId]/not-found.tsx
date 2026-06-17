/**
 * Not-found UI for the results route (W4-F2).
 *
 * Reached when the linked `sessionId` is not among the authenticated user's own
 * attempts (AttemptsRegion calls notFound()). Distinct from a service error:
 * the link simply does not point at one of this candidate's results.
 */
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function ResultsNotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Results not found</h1>
        <p className="text-sm text-slate-600">
          We couldn&apos;t find that attempt among your results. It may belong to a
          different account or the link may be incorrect.
        </p>
        <Button asChild>
          <Link href="/">Back to dashboard</Link>
        </Button>
      </div>
    </main>
  );
}
