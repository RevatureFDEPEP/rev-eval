'use client';

import { Component, type ReactNode } from 'react';
import { SectionErrorFallback } from './SectionErrorFallback';

interface SectionErrorBoundaryProps {
  /** Human label for the panel that failed, e.g. "summary" or "attempts". */
  title: string;
  children: ReactNode;
}

interface SectionErrorBoundaryState {
  hasError: boolean;
}

/**
 * Per-region boundary for CLIENT-side render errors (e.g. the chart throwing
 * during render). It does NOT catch failures inside an async server component:
 * a server-side fetch that throws propagates to the route-level error.tsx, not
 * here — so each region also try/catches its own fetch and renders
 * SectionErrorFallback inline (see results/[sessionId]/page.tsx). This boundary
 * is the client-render half of that two-part isolation.
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
    return <SectionErrorFallback title={this.props.title} onRetry={this.reset} />;
  }
}
