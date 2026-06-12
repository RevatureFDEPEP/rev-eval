import { describe, it, expect } from 'vitest';
import { computeProgress, getTimerState } from './quiz';

describe('computeProgress', () => {
  it('returns the correct percentage rounded to the nearest integer', () => {
    expect(computeProgress(7, 20)).toBe(35);
    expect(computeProgress(1, 3)).toBe(33); // 33.33... rounds down
  });

  it('caps the result at 100 and handles zero total gracefully', () => {
    expect(computeProgress(25, 20)).toBe(100); // over-answered → capped
    expect(computeProgress(5, 0)).toBe(0);    // zero total → 0
  });
});

describe('getTimerState', () => {
  it('returns "critical" when under 60 seconds remain', () => {
    expect(getTimerState(59)).toBe('critical');
    expect(getTimerState(0)).toBe('critical');
  });

  it('returns "warning" for 60–299 seconds and "normal" at 300+', () => {
    expect(getTimerState(60)).toBe('warning');
    expect(getTimerState(299)).toBe('warning');
    expect(getTimerState(300)).toBe('normal');
    expect(getTimerState(3600)).toBe('normal');
  });
});
