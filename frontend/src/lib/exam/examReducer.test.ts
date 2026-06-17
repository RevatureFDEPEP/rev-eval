import { describe, expect, it } from 'vitest';
import { examReducer, initialExamState } from './examReducer';

describe('examReducer', () => {
  it('SUBMIT_START optimistically locks before the server responds', () => {
    const s = examReducer(initialExamState, { type: 'SUBMIT_START' });
    expect(s.status).toBe('submitting');
    expect(s.isLocked).toBe(true);
    expect(s.error).toBeNull();
  });

  it('SUBMIT_CONFIRMED non-final unlocks for the next question', () => {
    const submitting = examReducer(initialExamState, { type: 'SUBMIT_START' });
    const s = examReducer(submitting, { type: 'SUBMIT_CONFIRMED', finalized: false });
    expect(s.status).toBe('active');
    expect(s.isLocked).toBe(false);
  });

  it('SUBMIT_CONFIRMED finalized stays locked and records submittedAt', () => {
    const submitting = examReducer(initialExamState, { type: 'SUBMIT_START' });
    const s = examReducer(submitting, {
      type: 'SUBMIT_CONFIRMED',
      finalized: true,
      submittedAt: '2026-06-16T10:00:00Z',
    });
    expect(s.status).toBe('submitted');
    expect(s.isLocked).toBe(true);
    expect(s.submittedAt).toBe('2026-06-16T10:00:00Z');
  });

  it('SUBMIT_FAILED keeps inputs locked so a rejected result is not editable', () => {
    const submitting = examReducer(initialExamState, { type: 'SUBMIT_START' });
    const s = examReducer(submitting, {
      type: 'SUBMIT_FAILED',
      kind: 'semantic',
      message: 'Session expired',
    });
    expect(s.status).toBe('error');
    expect(s.isLocked).toBe(true);
    expect(s.error).toEqual({ kind: 'semantic', message: 'Session expired' });
  });

  it('SUBMIT_RETRY re-enters submitting only for a transient error', () => {
    const transientErr = examReducer(
      examReducer(initialExamState, { type: 'SUBMIT_START' }),
      { type: 'SUBMIT_FAILED', kind: 'transient', message: 'network' },
    );
    const retried = examReducer(transientErr, { type: 'SUBMIT_RETRY' });
    expect(retried.status).toBe('submitting');
    expect(retried.isLocked).toBe(true);
  });

  it('SUBMIT_RETRY is a no-op for a semantic error (terminal)', () => {
    const semanticErr = examReducer(
      examReducer(initialExamState, { type: 'SUBMIT_START' }),
      { type: 'SUBMIT_FAILED', kind: 'semantic', message: '409' },
    );
    const retried = examReducer(semanticErr, { type: 'SUBMIT_RETRY' });
    expect(retried).toBe(semanticErr); // unchanged reference
  });
});
