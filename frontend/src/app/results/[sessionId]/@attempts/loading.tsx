/**
 * Suspense skeleton for the attempts table region — header + row placeholders
 * matching the final card shape.
 */
export default function AttemptsLoading() {
  return (
    <div className="animate-pulse rounded-xl border bg-card p-6" data-testid="attempts-skeleton">
      <div className="mb-5 h-5 w-36 rounded bg-muted" />
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-9 w-full rounded bg-muted" />
        ))}
      </div>
    </div>
  );
}
