/**
 * Exam-client error classification + retry (W3-F4 spec step 3).
 *
 * Network failures must not be treated the same as a server rejection:
 *   - TRANSIENT (network error, 502/503/504) → auto-retry with exponential
 *     backoff; the request may simply have hit a restarting/overloaded service.
 *   - SEMANTIC (409/410/422) → the server made a definitive decision (session
 *     locked/expired, payload invalid). Surface it and HALT — retrying would
 *     only storm the server with requests it has already refused.
 *
 * Anything else (4xx like 400/401/403/404, 5xx like 500) is treated as semantic:
 * better to halt and surface than to hammer a server that won't change its mind.
 */
import { ApiError } from '@/lib/api/client';
import type { ExamErrorKind } from '@/lib/api/types';

const SEMANTIC_STATUSES = new Set([409, 410, 422]);
const TRANSIENT_STATUSES = new Set([502, 503, 504]);

/** Map an HTTP status (or `undefined` for a network failure) to a retry policy. */
export function classifyError(status?: number): ExamErrorKind {
  if (status === undefined) return 'transient'; // network/connection failure
  if (SEMANTIC_STATUSES.has(status)) return 'semantic';
  if (TRANSIENT_STATUSES.has(status)) return 'transient';
  return 'semantic';
}

/** A classified exam-client failure carrying the retry policy + originating status. */
export class ExamError extends Error {
  constructor(
    public readonly kind: ExamErrorKind,
    public readonly status: number | undefined,
    message: string,
  ) {
    super(message);
    this.name = 'ExamError';
  }
}

interface RetryOptions {
  maxRetries?: number;
  baseMs?: number;
  /** Injectable delay (defaults to setTimeout) so tests can run without real waits. */
  sleep?: (ms: number) => Promise<void>;
}

const defaultSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Run `fn`, retrying ONLY transient failures with exponential backoff
 * (baseMs, 2·baseMs, 4·baseMs, …). Semantic failures throw immediately — no
 * retry storm on a 422/409. After `maxRetries` exhausted transient attempts the
 * last failure is rethrown as an {@link ExamError}.
 */
export async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const { maxRetries = 3, baseMs = 500, sleep = defaultSleep } = options;
  let attempt = 0;

  for (;;) {
    try {
      return await fn();
    } catch (err) {
      const status = err instanceof ApiError ? err.status : undefined;
      const kind = classifyError(status);
      const message = err instanceof Error ? err.message : 'Request failed';

      if (kind === 'semantic' || attempt >= maxRetries) {
        throw err instanceof ExamError ? err : new ExamError(kind, status, message);
      }

      attempt += 1;
      await sleep(baseMs * 2 ** (attempt - 1));
    }
  }
}
