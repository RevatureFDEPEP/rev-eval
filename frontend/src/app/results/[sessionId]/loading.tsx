import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card';

function Shimmer({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />;
}

/** Placeholder cards matching the summary stat grid. */
export function SummarySkeleton() {
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <Shimmer className="h-3 w-24" />
        <Shimmer className="h-8 w-72" />
        <Shimmer className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="border border-slate-200">
            <CardHeader className="pb-2">
              <Shimmer className="h-4 w-24" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Shimmer className="h-8 w-16" />
              <Shimmer className="h-3 w-28" />
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

/** Placeholder matching the attempts table. */
export function AttemptsTableSkeleton() {
  return (
    <Card className="border border-slate-200">
      <CardHeader className="space-y-2">
        <Shimmer className="h-5 w-40" />
        <Shimmer className="h-3 w-56 max-w-full" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Shimmer key={i} className="h-9 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}

/** Placeholder matching the chart card. */
export function ChartSkeleton() {
  return (
    <Card className="border border-slate-200">
      <CardHeader className="space-y-2">
        <Shimmer className="h-5 w-44" />
        <Shimmer className="h-3 w-56 max-w-full" />
      </CardHeader>
      <CardContent>
        <Shimmer className="h-[300px] w-full" />
      </CardContent>
    </Card>
  );
}

/** Route-level skeleton shown while the page chrome streams in. */
export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-6xl space-y-8 p-4 sm:p-6 lg:p-8">
      <SummarySkeleton />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AttemptsTableSkeleton />
        <ChartSkeleton />
      </div>
    </main>
  );
}
