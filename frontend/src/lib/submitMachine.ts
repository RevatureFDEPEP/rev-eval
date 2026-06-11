/**
 * Submit state machine — 6 states for quiz submission.
 *
 * Extracted as a pure reducer so it can be 100%-tested without React.
 */

export type SubmitState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'submitted' }
  | { status: 'error_recoverable'; message: string }
  | { status: 'error_terminal_409'; message: string }  // already submitted — do not retry
  | { status: 'error_terminal_410'; message: string }; // session expired — cannot submit

export type SubmitAction =
  | { type: 'SUBMIT' }
  | { type: 'SUCCESS' }
  | { type: 'ERROR_RECOVERABLE'; message: string }
  | { type: 'ERROR_TERMINAL_409'; message: string }
  | { type: 'ERROR_TERMINAL_410'; message: string }
  | { type: 'RESET' };

export const SUBMIT_INITIAL_STATE: SubmitState = { status: 'idle' };

export function submitReducer(state: SubmitState, action: SubmitAction): SubmitState {
  switch (action.type) {
    case 'SUBMIT':
      if (state.status === 'idle' || state.status === 'error_recoverable') {
        return { status: 'submitting' };
      }
      return state; // ignore double-submit or submit from terminal state

    case 'SUCCESS':
      return { status: 'submitted' };

    case 'ERROR_RECOVERABLE':
      return { status: 'error_recoverable', message: action.message };

    case 'ERROR_TERMINAL_409':
      return { status: 'error_terminal_409', message: action.message };

    case 'ERROR_TERMINAL_410':
      return { status: 'error_terminal_410', message: action.message };

    case 'RESET':
      return { status: 'idle' };

  }
}

/** Returns true when the submit button should be enabled. */
export function canSubmit(state: SubmitState): boolean {
  return state.status === 'idle' || state.status === 'error_recoverable';
}

/** Returns true for 409 and 410 errors that block any retry. */
export function isTerminalError(state: SubmitState): boolean {
  return state.status === 'error_terminal_409' || state.status === 'error_terminal_410';
}
