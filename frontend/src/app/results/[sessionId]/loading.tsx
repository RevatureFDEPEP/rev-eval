/**
 * Suspense skeleton for the summary headline region — placeholder cards
 * matching the final 4-card grid so the layout doesn't shift on resolve.
 */
export default function SummaryLoading() {
  return (
    <div className="space-y-3" data-testid="summary-skeleton">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="animate-pulse rounded-xl border bg-card p-6">
            <div className="mb-3 h-4 w-24 rounded bg-muted" />
            <div className="h-7 w-16 rounded bg-muted" />
          </div>
        ))}
      </div>
      <div className="h-4 w-72 animate-pulse rounded bg-muted" />
    </div>
  );
}
