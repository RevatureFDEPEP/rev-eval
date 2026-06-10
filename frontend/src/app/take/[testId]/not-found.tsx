/**
 * 404 page for /take/[testId] (W3-F7 item 5): the testId doesn't match a
 * test — surfaced by page.tsx calling notFound() on a 404 from the mint.
 */
import Link from 'next/link';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function TakeNotFound() {
  return (
    <div className="mx-auto max-w-2xl p-6" data-testid="take-not-found">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Test not found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600">
          <p>
            This test doesn&apos;t exist or is no longer available. Check the
            link you were given, or contact your trainer.
          </p>
          <Link href="/" className="text-sm font-medium text-blue-600 underline">
            Back to your dashboard
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
