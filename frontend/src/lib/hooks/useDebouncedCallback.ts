'use client';

import { useCallback, useEffect, useRef } from 'react';

/**
 * Returns a debounced wrapper around `callback`: rapid calls coalesce, and the
 * callback fires once `delayMs` after the last call. Used on the dashboard's
 * keystroke-driven filter inputs (date range) so typing doesn't fire a
 * navigation per character; the test-selector dropdown writes immediately.
 *
 * No external dependency — there is no debounce lib in the project.
 */
export function useDebouncedCallback<Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number,
): (...args: Args) => void {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // Keep the latest callback without resetting the timer.
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Clear any pending call on unmount.
  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return useCallback(
    (...args: Args) => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => callbackRef.current(...args), delayMs);
    },
    [delayMs],
  );
}
