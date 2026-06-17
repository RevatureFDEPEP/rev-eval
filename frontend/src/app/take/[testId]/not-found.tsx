import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TakeTestNotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg">Test not found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">That test link is not available.</p>
          <Button asChild>
            <a href="/participant/tests">Back to tests</a>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
