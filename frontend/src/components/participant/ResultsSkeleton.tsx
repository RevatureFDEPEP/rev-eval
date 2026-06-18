/**
 * ResultsSkeleton — loading placeholder for the quiz results page.
 *
 * Mirrors the final layout (headline + donut + stat rows) so the page does not
 * jump when the real data resolves.
 */
import { Card, CardContent, CardHeader } from '@/components/ui/card';

export function ResultsSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4">
      <div className="space-y-2">
        <div className="h-7 w-48 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-72 animate-pulse rounded bg-slate-100" />
      </div>
      <Card>
        <CardHeader>
          <div className="h-5 w-32 animate-pulse rounded bg-slate-200" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 items-center gap-6 sm:grid-cols-2">
            <div className="mx-auto size-[220px] animate-pulse rounded-full bg-slate-200" />
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-6 w-full animate-pulse rounded bg-slate-100" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
