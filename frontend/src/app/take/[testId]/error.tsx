'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TakeTestError({ reset }: { reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md border-red-200">
        <CardHeader>
          <CardTitle className="text-lg text-red-950">Unable to load quiz</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">Please retry or return to your tests.</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={reset}>
              Retry
            </Button>
            <Button asChild variant="outline">
              <a href="/participant/tests">Back to tests</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
