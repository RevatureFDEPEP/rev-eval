/**
 * Exam fetch error classification (W3-F4, spec step 3).
 *
 * Splits failures into:
 *  - **transient** — network failure (no status) or 502/503/504. Worth retrying
 *    with exponential backoff; the condition may clear.
 *  - **semantic** — 409/410/422 (and any other definite status). Surface and
 *    halt; retrying cannot succeed and a terminal/expired-session 409 must not
 *    retry-storm.
 */

import { ApiError } from '@/lib/api/client';
import type { ExamErrorKind } from '@/lib/api/types';

const TRANSIENT_STATUSES = new Set([502, 503, 504]);

/** Classify by HTTP status. `undefined` means a network-level failure. */
export function classifyError(status?: number): ExamErrorKind {
  if (status === undefined) return 'transient';
  if (TRANSIENT_STATUSES.has(status)) return 'transient';
  return 'semantic';
}

/** Pull the HTTP status from a thrown error, if it carries one. */
export function errorStatus(err: unknown): number | undefined {
  return err instanceof ApiError ? err.status : undefined;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

interface RetryOptions {
  maxRetries?: number;
  baseMs?: number;
}

/**
 * Run `fn`, retrying only on **transient** failures with exponential backoff
 * (baseMs, 2·baseMs, 4·baseMs, …). Semantic failures throw immediately, and the
 * original error is rethrown once retries are exhausted.
 */
export async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  { maxRetries = 3, baseMs = 300 }: RetryOptions = {}
): Promise<T> {
  let attempt = 0;
  for (;;) {
    try {
      return await fn();
    } catch (err) {
      const kind = classifyError(errorStatus(err));
      if (kind === 'semantic' || attempt >= maxRetries) {
        throw err;
      }
      await sleep(baseMs * 2 ** attempt);
      attempt += 1;
    }
  }
}
