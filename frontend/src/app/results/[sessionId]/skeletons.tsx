/**
 * Loading skeletons for the results page (W4-F2).
 *
 * No Skeleton primitive exists in the design system, so these are plain
 * `animate-pulse` placeholders shaped like the real regions. Shared by the
 * route-level `loading.tsx` and each region's Suspense fallback so the chrome
 * renders on first byte and the placeholder is replaced as each region streams.
 */
const bar = 'animate-pulse rounded bg-slate-200';

export function SummarySkeleton() {
  return (
    <section className="space-y-4" aria-hidden="true">
      <div className={`${bar} h-6 w-40`} />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-slate-200 p-6">
            <div className={`${bar} h-4 w-20`} />
            <div className={`${bar} mt-3 h-7 w-16`} />
          </div>
        ))}
      </div>
    </section>
  );
}

export function TableSkeleton() {
  return (
    <section className="space-y-3" aria-hidden="true">
      <div className={`${bar} h-6 w-36`} />
      <div className="space-y-2 rounded-md border border-slate-200 p-4">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className={`${bar} h-8 w-full`} />
        ))}
      </div>
    </section>
  );
}

export function ChartSkeleton() {
  return (
    <section className="space-y-3" aria-hidden="true">
      <div className={`${bar} h-6 w-28`} />
      <div className={`${bar} h-[280px] w-full`} />
    </section>
  );
}
