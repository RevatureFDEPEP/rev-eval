/**
 * Duration / score display helpers for the results surfaces (W4-F2).
 */

/**
 * Format a duration in seconds as a compact human string.
 *
 * @example
 * formatDuration(45)    // "45s"
 * formatDuration(312)   // "5m 12s"
 * formatDuration(5025)  // "1h 23m"
 * formatDuration(null)  // "—"
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—';
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/**
 * Format a 0–100 percentage score to one decimal place.
 *
 * @example
 * formatScore(82.456) // "82.5%"
 * formatScore(null)   // "—"
 */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return '—';
  return `${(Math.round(score * 10) / 10).toFixed(1)}%`;
}
