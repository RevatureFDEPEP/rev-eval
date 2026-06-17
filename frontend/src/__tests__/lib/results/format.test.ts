import { describe, expect, it } from 'vitest';

import {
  buildScoreSeries,
  formatDateTime,
  formatDuration,
  formatScorePct,
  scoreToPercent,
} from '@/lib/results/format';
import type { ReportAttemptItem } from '@/lib/api/types';

function attempt(overrides: Partial<ReportAttemptItem>): ReportAttemptItem {
  return {
    session_id: 's',
    test_id: 1,
    status: 'SUBMITTED',
    score: 0.5,
    correct_count: 1,
    total_answered: 2,
    ...overrides,
  };
}

describe('formatScorePct', () => {
  it('renders a 0..1 fraction as a whole percent', () => {
    expect(formatScorePct(0.85)).toBe('85%');
    expect(formatScorePct(0)).toBe('0%');
    expect(formatScorePct(1)).toBe('100%');
  });

  it('rounds to the nearest percent', () => {
    expect(formatScorePct(0.857)).toBe('86%');
    expect(formatScorePct(0.854)).toBe('85%');
  });

  it('renders an em-dash for null/undefined/NaN', () => {
    expect(formatScorePct(null)).toBe('—');
    expect(formatScorePct(undefined)).toBe('—');
    expect(formatScorePct(NaN)).toBe('—');
  });
});

describe('scoreToPercent', () => {
  it('converts fraction to integer percent', () => {
    expect(scoreToPercent(0.5)).toBe(50);
  });

  it('passes null through for missing scores', () => {
    expect(scoreToPercent(null)).toBeNull();
    expect(scoreToPercent(undefined)).toBeNull();
  });
});

describe('formatDuration', () => {
  it('formats sub-minute, sub-hour, and hour+ durations', () => {
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(90)).toBe('1m 30s');
    expect(formatDuration(3661)).toBe('1h 1m');
    expect(formatDuration(3600)).toBe('1h 0m');
    expect(formatDuration(0)).toBe('0s');
  });

  it('renders an em-dash for null/negative/NaN', () => {
    expect(formatDuration(null)).toBe('—');
    expect(formatDuration(undefined)).toBe('—');
    expect(formatDuration(-5)).toBe('—');
    expect(formatDuration(NaN)).toBe('—');
  });
});

describe('formatDateTime', () => {
  it('renders an em-dash for null/empty/unparseable', () => {
    expect(formatDateTime(null)).toBe('—');
    expect(formatDateTime(undefined)).toBe('—');
    expect(formatDateTime('')).toBe('—');
    expect(formatDateTime('not-a-date')).toBe('—');
  });

  it('renders a real timestamp as something other than the em-dash', () => {
    const out = formatDateTime('2026-06-17T10:30:00Z');
    expect(out).not.toBe('—');
    expect(out).toMatch(/2026/);
  });
});

describe('buildScoreSeries', () => {
  it('drops attempts with no score', () => {
    const series = buildScoreSeries([
      attempt({ session_id: 'a', score: 0.8 }),
      attempt({ session_id: 'b', score: null }),
    ]);
    expect(series.map((p) => p.sessionId)).toEqual(['a']);
  });

  it('reverses to oldest-first for the X axis', () => {
    // input is newest-first (as the API returns it)
    const series = buildScoreSeries([
      attempt({ session_id: 'newest', score: 0.9 }),
      attempt({ session_id: 'oldest', score: 0.4 }),
    ]);
    expect(series.map((p) => p.sessionId)).toEqual(['oldest', 'newest']);
  });

  it('flags only the featured attempt', () => {
    const series = buildScoreSeries(
      [
        attempt({ session_id: 'a', score: 0.8 }),
        attempt({ session_id: 'b', score: 0.6 }),
      ],
      'b',
    );
    expect(series.find((p) => p.sessionId === 'b')?.featured).toBe(true);
    expect(series.find((p) => p.sessionId === 'a')?.featured).toBe(false);
  });

  it('labels with the test name, falling back to the test id', () => {
    const series = buildScoreSeries([
      attempt({ session_id: 'a', test_id: 7, test_name: 'Algorithms', score: 0.8 }),
      attempt({ session_id: 'b', test_id: 9, test_name: null, score: 0.6 }),
      attempt({ session_id: 'c', test_id: 3, test_name: '  ', score: 0.6 }),
    ]);
    const byId = Object.fromEntries(series.map((p) => [p.sessionId, p.label]));
    expect(byId.a).toBe('Algorithms');
    expect(byId.b).toBe('Test 9');
    expect(byId.c).toBe('Test 3');
  });

  it('converts score fractions to whole-percent heights', () => {
    const series = buildScoreSeries([attempt({ session_id: 'a', score: 0.75 })]);
    expect(series[0].scorePct).toBe(75);
  });
});
