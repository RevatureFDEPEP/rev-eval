'use client';

/**
 * RegionErrorBoundary (W4-F2).
 *
 * Next's route-level `error.tsx` is segment-scoped — it blanks the whole page.
 * The spec requires that a failure in one region (a 500 from the reporting
 * service while streaming the summary, table, or chart) blank ONLY that panel
 * and offer a retry. A client error boundary per region delivers that.
 *
 * Critical detail: `notFound()` / `redirect()` work by throwing a control-flow
 * error (digest prefixed `NEXT_`). A naive boundary would swallow those and
 * break the page's ownership check, so they are re-thrown to reach Next's own
 * boundary. Retry re-runs the server render via `router.refresh()`.
 */
import { Component, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

function isNextControlFlow(error: unknown): boolean {
  const digest = (error as { digest?: unknown } | null)?.digest;
  return typeof digest === 'string' && digest.startsWith('NEXT_');
}

function RegionErrorFallback({
  label,
  onRetry,
}: {
  label: string;
  onRetry: () => void;
}) {
  const router = useRouter();
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-md border border-red-200 bg-red-50 p-4"
    >
      <p className="text-sm text-red-800">
        We couldn&apos;t load {label}. The rest of the page is unaffected.
      </p>
      <Button
        size="sm"
        variant="outline"
        onClick={() => {
          onRetry();
          router.refresh();
        }}
      >
        Try again
      </Button>
    </div>
  );
}

interface Props {
  /** Lower-case region name woven into the fallback copy, e.g. "the chart". */
  label: string;
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class RegionErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  private reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error) {
      // Let control-flow errors (notFound/redirect) propagate to Next.
      if (isNextControlFlow(error)) throw error;
      return <RegionErrorFallback label={this.props.label} onRetry={this.reset} />;
    }
    return this.props.children;
  }
}
