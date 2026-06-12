/** Returns progress as a 0–100 integer, capped at 100. */
export function computeProgress(answeredCount: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(100, Math.round((answeredCount / total) * 100));
}

export type TimerState = 'critical' | 'warning' | 'normal';

/** Maps seconds remaining to a timer urgency state. */
export function getTimerState(secondsRemaining: number): TimerState {
  if (secondsRemaining < 60) return 'critical';
  if (secondsRemaining < 300) return 'warning';
  return 'normal';
}
