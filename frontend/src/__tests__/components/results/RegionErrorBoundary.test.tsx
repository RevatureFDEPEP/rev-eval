import { render, screen } from '@testing-library/react';
import { Component, type ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { RegionErrorBoundary } from '@/components/results/RegionErrorBoundary';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

function Boom({ error }: { error: unknown }): ReactNode {
  throw error;
}

/** Outer boundary used only to prove control-flow errors are RE-thrown past
 *  RegionErrorBoundary instead of being swallowed by its panel fallback. */
class Catcher extends Component<{ children: ReactNode }, { caught: boolean }> {
  state = { caught: false };
  static getDerivedStateFromError() {
    return { caught: true };
  }
  render() {
    return this.state.caught ? <div>outer-caught</div> : this.props.children;
  }
}

describe('RegionErrorBoundary', () => {
  afterEach(() => vi.restoreAllMocks());

  it('renders children when nothing throws', () => {
    render(
      <RegionErrorBoundary label="the chart">
        <div>healthy content</div>
      </RegionErrorBoundary>,
    );
    expect(screen.getByText('healthy content')).toBeInTheDocument();
  });

  it('isolates a real error to a retryable panel', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <RegionErrorBoundary label="the chart">
        <Boom error={new Error('reporting 500')} />
      </RegionErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load the chart/i);
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('re-throws Next control-flow errors (notFound/redirect) to the parent', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const notFoundError = Object.assign(new Error('NEXT_HTTP_ERROR_FALLBACK'), {
      digest: 'NEXT_HTTP_ERROR_FALLBACK;404',
    });
    render(
      <Catcher>
        <RegionErrorBoundary label="your attempt history">
          <Boom error={notFoundError} />
        </RegionErrorBoundary>
      </Catcher>,
    );
    // The region boundary did NOT render its own fallback; the outer caught it.
    expect(screen.getByText('outer-caught')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
