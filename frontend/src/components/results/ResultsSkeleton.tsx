export default function ResultsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading results">
      {/* Header */}
      <div className="space-y-2">
        <div className="h-4 w-32 rounded bg-slate-200" />
        <div className="h-8 w-64 rounded bg-slate-200" />
        <div className="h-4 w-48 rounded bg-slate-200" />
      </div>

      {/* Score card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-center gap-6">
          <div className="h-20 w-20 rounded-full bg-slate-200" />
          <div className="space-y-2">
            <div className="h-4 w-24 rounded bg-slate-200" />
            <div className="h-10 w-32 rounded bg-slate-200" />
            <div className="h-4 w-40 rounded bg-slate-200" />
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <div className="h-3 w-20 rounded bg-slate-200" />
            <div className="h-7 w-12 rounded bg-slate-200" />
          </div>
        ))}
      </div>

      {/* Chart area */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-3">
        <div className="h-5 w-48 rounded bg-slate-200" />
        <div className="h-56 w-full rounded bg-slate-100" />
      </div>
    </div>
  );
}
