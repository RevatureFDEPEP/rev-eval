import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { ExamError } from '@/lib/exam/errors';
import { AuthProvider } from '@/lib/auth/AuthContext';
import type { AnswerResult, SanitizedQuestion, SessionResponse } from '@/lib/api/types';
import { TestRunner } from './TestRunner';

const IDENTITY = { userId: 42, email: 'student2@revature.com', role: 'PARTICIPANT' };

const MCQ: SanitizedQuestion = {
  id: 'q-mcq',
  type: 'mcq',
  question_text: '2 + 2?',
  options: [
    { option_id: 1, text: 'Three' },
    { option_id: 2, text: 'Four' },
  ],
  difficulty: 'easy',
};

// Far-future expiry so the server-anchored timer never auto-submits mid-test.
function makeSession(overrides: Partial<SessionResponse> = {}): SessionResponse {
  const now = new Date();
  return {
    session_id: 'sess-1',
    session_token: 't'.repeat(64),
    server_now: now.toISOString(),
    expires_at: new Date(now.getTime() + 60 * 60 * 1000).toISOString(),
    current_index: 0,
    total_questions: 1,
    question: MCQ,
    draft_answers: null,
    ...overrides,
  };
}

function renderRunner(props: Partial<React.ComponentProps<typeof TestRunner>> = {}) {
  const session = props.session ?? makeSession();
  return render(
    <AuthProvider identity={IDENTITY}>
      <TestRunner
        session={session}
        submitAnswerFn={props.submitAnswerFn}
        saveDraftFn={props.saveDraftFn ?? vi.fn().mockResolvedValue(undefined)}
      />
    </AuthProvider>,
  );
}

describe('TestRunner submit-and-lock (W3-F4)', () => {
  it('locks inputs while a submit is in flight', async () => {
    // A never-resolving submit keeps the exam in the `submitting` state.
    const pending = new Promise<AnswerResult>(() => {});
    renderRunner({ submitAnswerFn: vi.fn().mockReturnValue(pending) });

    fireEvent.click(screen.getByLabelText('Four')); // select so submit enables
    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(screen.getByTestId('submit-button')).toBeDisabled();
    });
    // The radio group reflects the optimistic lock.
    expect(screen.getByRole('radiogroup')).toHaveAttribute('aria-disabled', 'true');
  });

  it('renders the locked confirmation once the final answer is accepted', async () => {
    const submit = vi.fn().mockResolvedValue({
      question_id: 'q-mcq',
      current_index: 1,
      total_questions: 1,
      status: 'SUBMITTED',
      submitted_at: '2026-06-16T10:00:00Z',
      next_question: null,
    } satisfies AnswerResult);
    renderRunner({ submitAnswerFn: submit });

    fireEvent.click(screen.getByLabelText('Four'));
    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(screen.getByTestId('exam-confirmation')).toBeInTheDocument();
    });
    // No interactive inputs survive the lock.
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument();
  });

  it('passes a stable idempotency key across a transient retry', async () => {
    const { ExamError } = await import('@/lib/exam/errors');
    const submit = vi
      .fn()
      .mockRejectedValueOnce(new ExamError('transient', 503, 'network'))
      .mockResolvedValue({
        question_id: 'q-mcq',
        current_index: 1,
        total_questions: 1,
        status: 'SUBMITTED',
        submitted_at: '2026-06-16T10:00:00Z',
        next_question: null,
      } satisfies AnswerResult);
    renderRunner({ submitAnswerFn: submit });

    fireEvent.click(screen.getByLabelText('Four'));
    fireEvent.click(screen.getByTestId('submit-button'));

    // Transient failure surfaces a Retry button.
    await waitFor(() => expect(screen.getByTestId('retry-button')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('retry-button'));

    await waitFor(() => expect(screen.getByTestId('exam-confirmation')).toBeInTheDocument());
    // Same idempotency key on both calls (4th arg) → retry replays, not rescores.
    const key1 = submit.mock.calls[0][3];
    const key2 = submit.mock.calls[1][3];
    expect(key1).toBeTruthy();
    expect(key2).toBe(key1);
  });

  it('seeds answers from a resumed session draft', () => {
    renderRunner({
      session: makeSession({ draft_answers: { 'q-mcq': [2] } }),
    });
    // The "Four" radio (option_id 2) starts checked from the draft.
    expect(screen.getByLabelText('Four')).toBeChecked();
  });

  it('converts TRUE_FALSE selection to a bool on submit', async () => {
    const submit = vi.fn().mockResolvedValue({
      question_id: 'q-tf',
      current_index: 1,
      total_questions: 1,
      status: 'SUBMITTED',
      submitted_at: null,
      next_question: null,
    } satisfies AnswerResult);
    const tf: SanitizedQuestion = {
      id: 'q-tf',
      type: 'true_false',
      question_text: 'Sky is blue?',
      options: null,
      difficulty: 'easy',
    };
    renderRunner({ session: makeSession({ question: tf }), submitAnswerFn: submit });

    fireEvent.click(screen.getByLabelText('True')); // synthesized option_id 1
    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalled());
    expect(submit.mock.calls[0][1]).toEqual([true]); // [1] → [true]
  });

  it('surfaces a semantic rejection with no retry affordance', async () => {
    // 409/410/422 are definitive server decisions — surface + halt, never retry.
    const submit = vi
      .fn()
      .mockRejectedValue(new ExamError('semantic', 409, 'Session already submitted'));
    renderRunner({ submitAnswerFn: submit });

    fireEvent.click(screen.getByLabelText('Four'));
    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('rejected by the server');
    });
    // Semantic failures get no Retry button — only transient ones do.
    expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
    expect(submit).toHaveBeenCalledTimes(1);
  });
});

describe('TestRunner live exam behaviour (W3-F4)', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('autosaves the in-progress answer map once the debounce interval elapses', async () => {
    vi.useFakeTimers();
    const saveDraft = vi.fn().mockResolvedValue(undefined);
    renderRunner({ saveDraftFn: saveDraft });

    fireEvent.click(screen.getByLabelText('Four')); // option_id 2 → answers map

    // Nothing saved before the 30s interval.
    expect(saveDraft).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(saveDraft).toHaveBeenCalledTimes(1);
    expect(saveDraft.mock.calls[0][0]).toBe('sess-1');
    expect(saveDraft.mock.calls[0][1]).toEqual({ 'q-mcq': [2] });
  });

  it('halts autosave permanently after a terminal 409 from the server', async () => {
    vi.useFakeTimers();
    // First save 409s (session terminal); a later edit must NOT PATCH again.
    const saveDraft = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(409, 'Conflict', 'submitted'))
      .mockResolvedValue(undefined);
    renderRunner({ saveDraftFn: saveDraft });

    fireEvent.click(screen.getByLabelText('Four'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(saveDraft).toHaveBeenCalledTimes(1); // the 409

    // Change the answer and let another full interval pass.
    fireEvent.click(screen.getByLabelText('Three'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(saveDraft).toHaveBeenCalledTimes(1); // still 1 — autosave latched off
  });

  it('auto-submits the frontier answer when the timer reaches zero', async () => {
    vi.useFakeTimers();
    const submit = vi.fn().mockResolvedValue({
      question_id: 'q-mcq',
      current_index: 1,
      total_questions: 1,
      status: 'SUBMITTED',
      submitted_at: '2026-06-16T10:00:00Z',
      next_question: null,
    } satisfies AnswerResult);
    // Expiry one second out — frozen-clock arithmetic under fake timers.
    const now = Date.now();
    const session = makeSession({
      server_now: new Date(now).toISOString(),
      expires_at: new Date(now + 1_000).toISOString(),
    });
    renderRunner({ session, submitAnswerFn: submit });

    // No selection, no button click — expiry alone must submit the frontier.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_100);
    });

    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit.mock.calls[0][2]).toBe('q-mcq'); // frontier question id
    expect(screen.getByTestId('exam-confirmation')).toBeInTheDocument();
  });
});
