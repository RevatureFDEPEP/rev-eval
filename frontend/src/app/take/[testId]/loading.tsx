import { Card, CardContent } from '@/components/ui/card';

export default function TakeTestLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md border-slate-200">
        <CardContent className="flex items-center gap-4 pt-6">
          <div className="size-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <div>
            <p className="text-sm font-medium text-slate-950">Starting quiz</p>
            <p className="text-xs text-slate-600">Preparing your session...</p>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
