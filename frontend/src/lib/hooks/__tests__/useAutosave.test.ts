import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { makeIdempotencyKey, useAutosave, type AutosaveAnswerValue } from '../useAutosave';

// ─── Pure function ────────────────────────────────────────────────────────────

describe('makeIdempotencyKey', () => {
  it('formats as session_id:question_id:attempt_n', () => {
    expect(makeIdempotencyKey('sess-1', 'q-42', 0)).toBe('sess-1:q-42:0');
    expect(makeIdempotencyKey('sess-1', 'q-42', 3)).toBe('sess-1:q-42:3');
  });

  it('handles string values with colons', () => {
    expect(makeIdempotencyKey('a:b', 'c:d', 1)).toBe('a:b:c:d:1');
  });
});

// ─── Hook ─────────────────────────────────────────────────────────────────────

describe('useAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not save immediately — respects debounce delay', () => {
    const answers = new Map<string, AutosaveAnswerValue>([['q1', 1]]);

    renderHook(() => useAutosave({ sessionId: 'sess-1', answers, delayMs: 400 }));

    // Before timer fires: nothing saved
    expect(localStorage.getItem('quiz-draft-sess-1')).toBeNull();

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(localStorage.getItem('quiz-draft-sess-1')).not.toBeNull();
  });

  it('saves draft with correct structure', () => {
    const answers = new Map<string, AutosaveAnswerValue>([['q-abc', 2]]);

    renderHook(() => useAutosave({ sessionId: 'sess-2', answers, delayMs: 400 }));

    act(() => {
      vi.advanceTimersByTime(400);
    });

    const saved = JSON.parse(localStorage.getItem('quiz-draft-sess-2') as string) as Array<{
      question_id: string;
      answer: AutosaveAnswerValue;
      idempotency_key: string;
    }>;

    expect(saved).toHaveLength(1);
    expect(saved[0].question_id).toBe('q-abc');
    expect(saved[0].answer).toBe(2);
    expect(saved[0].idempotency_key).toMatch(/^sess-2:q-abc:\d+$/);
  });

  it('does not save when sessionId is null', () => {
    const answers = new Map<string, AutosaveAnswerValue>([['q1', 1]]);

    renderHook(() => useAutosave({ sessionId: null, answers, delayMs: 400 }));

    act(() => {
      vi.advanceTimersByTime(400);
    });

    // Nothing keyed by "null" or the question
    expect(localStorage.length).toBe(0);
  });

  it('cancels previous timer and re-debounces when answers change', () => {
    let currentAnswers = new Map<string, AutosaveAnswerValue>([['q1', 1]]);

    const { rerender } = renderHook(
      ({ answers }: { answers: Map<string, AutosaveAnswerValue> }) =>
        useAutosave({ sessionId: 'sess-3', answers, delayMs: 400 }),
      { initialProps: { answers: currentAnswers } }
    );

    // Advance halfway through debounce
    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Change answers — should restart debounce
    currentAnswers = new Map([
      ['q1', 1],
      ['q2', 3],
    ]);
    rerender({ answers: currentAnswers });

    // 200ms more — 400ms since initial but only 200ms since latest change
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(localStorage.getItem('quiz-draft-sess-3')).toBeNull();

    // Final 200ms — now 400ms since last change
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(localStorage.getItem('quiz-draft-sess-3')).not.toBeNull();
  });

  it('saves multi-select and boolean answers', () => {
    const answers = new Map<string, AutosaveAnswerValue>([
      ['mcq-q', 0],
      ['multi-q', [1, 3]],
      ['tf-q', true],
    ]);

    renderHook(() => useAutosave({ sessionId: 'sess-4', answers, delayMs: 400 }));

    act(() => {
      vi.advanceTimersByTime(400);
    });

    const saved = JSON.parse(localStorage.getItem('quiz-draft-sess-4') as string) as Array<{
      question_id: string;
      answer: AutosaveAnswerValue;
    }>;

    const byId = Object.fromEntries(saved.map((e) => [e.question_id, e.answer]));
    expect(byId['mcq-q']).toBe(0);
    expect(byId['multi-q']).toEqual([1, 3]);
    expect(byId['tf-q']).toBe(true);
  });
});
