/**
 * Pure presentation helpers for the candidate results page (W4-F2).
 *
 * Kept free of React/recharts so the formatting and chart-shaping logic is
 * unit-testable in isolation. The reporting service returns `score` as a 0..1
 * fraction (null when an attempt has no scored answers) and durations in whole
 * seconds; these helpers turn those into display strings and chart series.
 */
import type { ReportAttemptItem } from '@/lib/api/types';

const EM_DASH = '—';

/** A 0..1 fraction → a whole-percent label ("85%"); em-dash for null/undefined. */
export function formatScorePct(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return EM_DASH;
  return `${Math.round(score * 100)}%`;
}

/** A 0..1 fraction → its whole-percent number (0..100); null passes through. */
export function scoreToPercent(score: number | null | undefined): number | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return Math.round(score * 100);
}

/** Whole seconds → "1h 5m" / "12m 30s" / "45s"; em-dash for null/negative. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return EM_DASH;
  if (seconds < 0) return EM_DASH;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** ISO timestamp → locale date-time; em-dash for null/unparseable. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return EM_DASH;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** A point on the score-per-attempt chart. */
export interface ScorePoint {
  sessionId: string;
  label: string;
  scorePct: number;
  featured: boolean;
}

/**
 * Build the score-per-attempt series for the BarChart.
 *
 * Only attempts with a non-null score contribute (an attempt with no answers
 * has nothing to plot). The reporting service returns attempts newest-first;
 * the chart reads oldest→newest left to right, so the series is reversed. The
 * attempt matching `featuredSessionId` is flagged so the chart can accent it.
 */
export function buildScoreSeries(
  attempts: ReportAttemptItem[],
  featuredSessionId?: string,
): ScorePoint[] {
  return attempts
    .filter((a) => a.score !== null && a.score !== undefined)
    .map((a) => ({
      sessionId: a.session_id,
      label: a.test_name?.trim() || `Test ${a.test_id}`,
      scorePct: scoreToPercent(a.score) ?? 0,
      featured: a.session_id === featuredSessionId,
    }))
    .reverse();
}
