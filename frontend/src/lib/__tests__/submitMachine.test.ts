import { describe, it, expect } from 'vitest';
import {
  submitReducer,
  SUBMIT_INITIAL_STATE,
  canSubmit,
  isTerminalError,
  type SubmitState,
} from '../submitMachine';

describe('SUBMIT_INITIAL_STATE', () => {
  it('is idle', () => {
    expect(SUBMIT_INITIAL_STATE).toEqual({ status: 'idle' });
  });
});

describe('submitReducer — SUBMIT action', () => {
  it('idle + SUBMIT → submitting', () => {
    expect(submitReducer({ status: 'idle' }, { type: 'SUBMIT' })).toEqual({
      status: 'submitting',
    });
  });

  it('error_recoverable + SUBMIT → submitting (retry allowed)', () => {
    const state: SubmitState = { status: 'error_recoverable', message: 'timeout' };
    expect(submitReducer(state, { type: 'SUBMIT' })).toEqual({ status: 'submitting' });
  });

  it('submitting + SUBMIT → stays submitting (prevents double-submit)', () => {
    expect(submitReducer({ status: 'submitting' }, { type: 'SUBMIT' })).toEqual({
      status: 'submitting',
    });
  });

  it('submitted + SUBMIT → stays submitted', () => {
    expect(submitReducer({ status: 'submitted' }, { type: 'SUBMIT' })).toEqual({
      status: 'submitted',
    });
  });

  it('error_terminal_409 + SUBMIT → stays terminal (no retry)', () => {
    const state: SubmitState = { status: 'error_terminal_409', message: 'done' };
    expect(submitReducer(state, { type: 'SUBMIT' })).toEqual(state);
  });

  it('error_terminal_410 + SUBMIT → stays terminal (no retry)', () => {
    const state: SubmitState = { status: 'error_terminal_410', message: 'expired' };
    expect(submitReducer(state, { type: 'SUBMIT' })).toEqual(state);
  });
});

describe('submitReducer — SUCCESS action', () => {
  it('submitting + SUCCESS → submitted', () => {
    expect(submitReducer({ status: 'submitting' }, { type: 'SUCCESS' })).toEqual({
      status: 'submitted',
    });
  });
});

describe('submitReducer — ERROR_RECOVERABLE action', () => {
  it('submitting + ERROR_RECOVERABLE → error_recoverable with message', () => {
    expect(
      submitReducer({ status: 'submitting' }, { type: 'ERROR_RECOVERABLE', message: 'network' })
    ).toEqual({ status: 'error_recoverable', message: 'network' });
  });
});

describe('submitReducer — ERROR_TERMINAL_409 action', () => {
  it('submitting + ERROR_TERMINAL_409 → error_terminal_409', () => {
    expect(
      submitReducer(
        { status: 'submitting' },
        { type: 'ERROR_TERMINAL_409', message: 'already submitted' }
      )
    ).toEqual({ status: 'error_terminal_409', message: 'already submitted' });
  });
});

describe('submitReducer — ERROR_TERMINAL_410 action', () => {
  it('submitting + ERROR_TERMINAL_410 → error_terminal_410', () => {
    expect(
      submitReducer(
        { status: 'submitting' },
        { type: 'ERROR_TERMINAL_410', message: 'session expired' }
      )
    ).toEqual({ status: 'error_terminal_410', message: 'session expired' });
  });
});

describe('submitReducer — RESET action', () => {
  const nonIdleStates: SubmitState[] = [
    { status: 'submitting' },
    { status: 'submitted' },
    { status: 'error_recoverable', message: 'x' },
    { status: 'error_terminal_409', message: 'x' },
    { status: 'error_terminal_410', message: 'x' },
  ];

  nonIdleStates.forEach((state) => {
    it(`${state.status} + RESET → idle`, () => {
      expect(submitReducer(state, { type: 'RESET' })).toEqual({ status: 'idle' });
    });
  });
});

describe('canSubmit', () => {
  it('returns true for idle', () => {
    expect(canSubmit({ status: 'idle' })).toBe(true);
  });

  it('returns true for error_recoverable', () => {
    expect(canSubmit({ status: 'error_recoverable', message: 'x' })).toBe(true);
  });

  it('returns false for submitting', () => {
    expect(canSubmit({ status: 'submitting' })).toBe(false);
  });

  it('returns false for submitted', () => {
    expect(canSubmit({ status: 'submitted' })).toBe(false);
  });

  it('returns false for error_terminal_409', () => {
    expect(canSubmit({ status: 'error_terminal_409', message: 'x' })).toBe(false);
  });

  it('returns false for error_terminal_410', () => {
    expect(canSubmit({ status: 'error_terminal_410', message: 'x' })).toBe(false);
  });
});

describe('isTerminalError', () => {
  it('returns true for error_terminal_409', () => {
    expect(isTerminalError({ status: 'error_terminal_409', message: 'x' })).toBe(true);
  });

  it('returns true for error_terminal_410', () => {
    expect(isTerminalError({ status: 'error_terminal_410', message: 'x' })).toBe(true);
  });

  it('returns false for idle', () => {
    expect(isTerminalError({ status: 'idle' })).toBe(false);
  });

  it('returns false for submitting', () => {
    expect(isTerminalError({ status: 'submitting' })).toBe(false);
  });

  it('returns false for submitted', () => {
    expect(isTerminalError({ status: 'submitted' })).toBe(false);
  });

  it('returns false for error_recoverable', () => {
    expect(isTerminalError({ status: 'error_recoverable', message: 'x' })).toBe(false);
  });
});
