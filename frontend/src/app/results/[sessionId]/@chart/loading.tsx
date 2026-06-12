/**
 * Suspense skeleton for the chart region — bar-shaped placeholders at the
 * ChartWrapper's standard height.
 */
export default function ChartLoading() {
  return (
    <div className="animate-pulse rounded-xl border bg-card p-6" data-testid="chart-skeleton">
      <div className="mb-4 h-4 w-32 rounded bg-muted" />
      <div className="flex h-[280px] items-end gap-3">
        {[60, 35, 80, 50, 70, 45].map((h, i) => (
          <div key={i} className="flex-1 rounded-t bg-muted" style={{ height: `${h}%` }} />
        ))}
      </div>
    </div>
  );
}
