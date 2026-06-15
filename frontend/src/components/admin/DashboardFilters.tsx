/**
 * URL-synced, debounced filter controls for the trainer dashboard (W4-F4).
 *
 * Writes test/date selections into the query string via useRouter +
 * useSearchParams, so the server components re-render the filtered state with
 * no client loading flicker and the filtered view is shareable by URL. The
 * test-selector dropdown writes immediately; the date inputs are debounced
 * 300ms so typing doesn't fire a navigation per keystroke.
 */
'use client';

import { useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDebouncedCallback } from '@/lib/hooks/useDebouncedCallback';

interface TestOption {
  id: number;
  name: string;
}

interface DashboardFiltersProps {
  tests: TestOption[];
}

const ALL_TESTS = 'all';

export function DashboardFilters({ tests }: DashboardFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentTest = searchParams.get('test_id') ?? ALL_TESTS;
  const currentFrom = searchParams.get('from') ?? '';
  const currentTo = searchParams.get('to') ?? '';

  // Merge one key into the current query string and navigate (shareable URL).
  const setParam = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === null || value === '') params.delete(key);
      else params.set(key, value);
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : '?', { scroll: false });
    },
    [router, searchParams],
  );

  // Dropdown writes immediately; date inputs are debounced (keystroke-driven).
  const setDateParam = useDebouncedCallback(setParam, 300);

  return (
    <div className="flex flex-wrap items-end gap-4" data-testid="dashboard-filters">
      <div className="grid gap-1.5">
        <Label htmlFor="test-filter">Test</Label>
        <Select
          value={currentTest}
          onValueChange={(v) => setParam('test_id', v === ALL_TESTS ? null : v)}
        >
          <SelectTrigger id="test-filter" className="w-56">
            <SelectValue placeholder="All tests" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_TESTS}>All tests</SelectItem>
            {tests.map((t) => (
              <SelectItem key={t.id} value={String(t.id)}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="from-filter">From</Label>
        <Input
          id="from-filter"
          type="date"
          defaultValue={currentFrom}
          className="w-40"
          onChange={(e) => setDateParam('from', e.target.value || null)}
        />
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="to-filter">To</Label>
        <Input
          id="to-filter"
          type="date"
          defaultValue={currentTo}
          className="w-40"
          onChange={(e) => setDateParam('to', e.target.value || null)}
        />
      </div>
    </div>
  );
}
