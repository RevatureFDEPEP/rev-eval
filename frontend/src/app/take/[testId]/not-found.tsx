import Link from 'next/link';
import { Button } from '@/components/ui/button';

/** Shown when the test id is invalid or the test does not exist (404 on mint). */
export default function TakeNotFound() {
  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6 text-center">
      <h2 className="text-lg font-semibold">Test not found</h2>
      <p className="text-sm text-muted-foreground">
        This test doesn’t exist or is no longer available.
      </p>
      <Button asChild variant="outline">
        <Link href="/">Back to dashboard</Link>
      </Button>
    </div>
  );
}
