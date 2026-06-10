/**
 * examReducer — the submit-and-lock state machine (W3-F4 spec step 4).
 *
 * The lock is OPTIMISTIC for inputs/timer (set on `SUBMIT_START`, before the
 * server responds) but the *result* is a CONFIRMED update: only `SUBMIT_CONFIRMED`
 * reflects the server's decision. On failure we surface the error and KEEP the
 * inputs locked — a rejected submission must never be shown back as editable/
 * "succeeded".
 *
 *   active ──SUBMIT_START──▶ submitting ──SUBMIT_CONFIRMED(finalized)──▶ submitted (locked)
 *                                        └─SUBMIT_CONFIRMED(!finalized)─▶ active (unlocked, next q)
 *                                        └─SUBMIT_FAILED────────────────▶ error (locked)
 *   error(transient) ──SUBMIT_RETRY──▶ submitting (stays locked until the retry acks)
 *
 * Only a TRANSIENT failure (network blip, 502/503/504 after backoff exhaustion)
 * may be retried — a brief outage must not brick the attempt (W3-F7 item 2).
 * Semantic rejections (409/410/422) keep the terminal lock: the server has
 * made a definitive decision.
 */
import type { ExamErrorKind } from '@/lib/api/types';

export type ExamStatus = 'active' | 'submitting' | 'submitted' | 'error';

export interface ExamState {
  status: ExamStatus;
  isLocked: boolean; // inputs + timer disabled
  error: { kind: ExamErrorKind; message: string } | null;
  submittedAt: string | null;
}

export const initialExamState: ExamState = {
  status: 'active',
  isLocked: false,
  error: null,
  submittedAt: null,
};

export type ExamAction =
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_CONFIRMED'; finalized: boolean; submittedAt?: string | null }
  | { type: 'SUBMIT_FAILED'; kind: ExamErrorKind; message: string }
  | { type: 'SUBMIT_RETRY' };

export function examReducer(state: ExamState, action: ExamAction): ExamState {
  switch (action.type) {
    case 'SUBMIT_START':
      // Optimistic lock: disable inputs + timer immediately.
      return { ...state, status: 'submitting', isLocked: true, error: null };

    case 'SUBMIT_CONFIRMED':
      if (action.finalized) {
        // Final question accepted → terminal, stay locked, render confirmation.
        return {
          ...state,
          status: 'submitted',
          isLocked: true,
          error: null,
          submittedAt: action.submittedAt ?? null,
        };
      }
      // Non-final answer accepted → advance to the next question, unlock inputs.
      return { ...state, status: 'active', isLocked: false, error: null };

    case 'SUBMIT_FAILED':
      // Surface + halt; keep locked so a rejected result is not shown editable.
      return {
        ...state,
        status: 'error',
        isLocked: true,
        error: { kind: action.kind, message: action.message },
      };

    case 'SUBMIT_RETRY':
      // Exit `error` only for transient failures; semantic stays terminal.
      if (state.status !== 'error' || state.error?.kind !== 'transient') {
        return state;
      }
      return { ...state, status: 'submitting', isLocked: true, error: null };

    default:
      return state;
  }
}
