'use client';

import { Component, type ReactNode } from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface SectionErrorBoundaryProps {
  /** Human label for the panel that failed, e.g. "summary" or "attempts". */
  title: string;
  children: ReactNode;
}

interface SectionErrorBoundaryState {
  hasError: boolean;
}

/**
 * Per-region error boundary.
 *
 * Next.js `error.tsx` files are scoped to a whole route segment, so a single
 * one cannot isolate individual panels. This client boundary wraps each data
 * region (summary, table, chart) on its own: a failure (e.g. a 500 from the
 * reporting service while that region's server component renders) blanks only
 * that panel and offers a retry, leaving the rest of the page intact.
 */
export class SectionErrorBoundary extends Component<
  SectionErrorBoundaryProps,
  SectionErrorBoundaryState
> {
  state: SectionErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): SectionErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error(`Results "${this.props.title}" panel failed:`, error);
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
          <AlertTriangle className="h-6 w-6 text-red-500" aria-hidden="true" />
          <p className="text-sm text-red-800">
            We couldn&apos;t load the {this.props.title} right now.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={this.reset}
            className="border-red-300 text-red-700 hover:bg-red-100"
          >
            <RotateCw className="mr-2 h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }
}
