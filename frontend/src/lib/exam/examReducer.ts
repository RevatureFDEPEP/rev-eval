/**
 * Exam submit state machine (W3-F4, spec step 4).
 *
 * `status` is the single source of truth — lock/nav/timer states are derived
 * from it at the call site (no redundant isLocked field to drift):
 *  - SUBMIT_START → 'submitting': inputs + timer lock optimistically.
 *  - SUBMIT_CONFIRMED applies the server's verdict: a SUBMITTED status ends the
 *    exam ('submitted', show confirmation); otherwise back to 'active', with the
 *    answered question recorded so it renders read-only on review.
 *  - SUBMIT_FAILED → 'error': surface the error rather than a rejected result.
 *    Recoverable — the caller re-runs the submit (retry) to return to 'active'.
 */

import type { AnswerResult } from '@/lib/api/types';

export type ExamStatus = 'active' | 'submitting' | 'submitted' | 'error';

export interface ExamState {
  status: ExamStatus;
  answeredIndices: Set<number>;
  error: string | null;
}

export type ExamAction =
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_CONFIRMED'; result: AnswerResult }
  | { type: 'SUBMIT_FAILED'; error: string };

export const initialExamState: ExamState = {
  status: 'active',
  answeredIndices: new Set<number>(),
  error: null,
};

export function examReducer(state: ExamState, action: ExamAction): ExamState {
  switch (action.type) {
    case 'SUBMIT_START':
      // Optimistic lock — disable inputs + timer before the server responds.
      return { ...state, status: 'submitting', error: null };

    case 'SUBMIT_CONFIRMED': {
      const answeredIndices = new Set(state.answeredIndices);
      answeredIndices.add(action.result.question_index);
      const finished = action.result.session_status === 'SUBMITTED';
      return {
        ...state,
        status: finished ? 'submitted' : 'active',
        answeredIndices,
        error: null,
      };
    }

    case 'SUBMIT_FAILED':
      // Surface the error; the caller can retry, which returns us to 'active'.
      return { ...state, status: 'error', error: action.error };

    default:
      return state;
  }
}
