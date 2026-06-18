/**
 * Display formatting helpers for the results / reporting views.
 */

/**
 * Format a duration given in seconds as a compact human string.
 *
 * @example
 * formatDuration(0)      // "0s"
 * formatDuration(45)     // "45s"
 * formatDuration(90)     // "1m 30s"
 * formatDuration(3661)   // "1h 1m"
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) {
    return '0s';
  }

  const total = Math.floor(seconds);
  const hrs = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hrs > 0) {
    return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
  }
  if (mins > 0) {
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  return `${secs}s`;
}

/**
 * Format a numeric score (0–100 scale) as a rounded percentage string.
 *
 * @example
 * formatScore(87.4) // "87%"
 * formatScore(null) // "—"
 */
export function formatScore(score: number | null | undefined): string {
  if (score == null || !Number.isFinite(score)) {
    return '—';
  }
  return `${Math.round(score)}%`;
}
