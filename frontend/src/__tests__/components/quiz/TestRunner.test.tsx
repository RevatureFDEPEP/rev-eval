import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api/sessions', () => ({
  submitAnswer: vi.fn(),
  saveDraft: vi.fn().mockResolvedValue({}),
}))

import { submitAnswer } from '@/lib/api/sessions'
import { ApiError } from '@/lib/api/client'
import { TestRunner } from '@/components/quiz/TestRunner'
import {
  AnswerResult,
  ParticipantQuestion,
  SessionResponse,
} from '@/lib/api/types'

const Q1: ParticipantQuestion = {
  id: 'q1',
  type: 'mcq',
  question_text: 'Capital of France?',
  options: [
    { option_id: 1, text: 'Paris' },
    { option_id: 2, text: 'Lyon' },
  ],
  index: 0,
}
const Q2: ParticipantQuestion = {
  id: 'q2',
  type: 'multi',
  question_text: 'Which are prime?',
  options: [
    { option_id: 10, text: 'Two' },
    { option_id: 11, text: 'Four' },
    { option_id: 12, text: 'Three' },
  ],
  index: 1,
}
const Q3: ParticipantQuestion = {
  id: 'q3',
  type: 'mcq',
  question_text: 'Largest planet?',
  options: [
    { option_id: 20, text: 'Jupiter' },
    { option_id: 21, text: 'Mars' },
  ],
  index: 2,
}

// A 30-minute window anchored so the timer never expires during a test.
function session(overrides: Partial<SessionResponse> = {}): SessionResponse {
  return {
    session_id: 's1',
    session_token: 'tok',
    status: 'ACTIVE',
    server_now: '2026-06-11T10:00:00Z',
    expires_at: '2026-06-11T10:30:00Z',
    total_questions: 3,
    current_index: 0,
    question: Q1,
    ...overrides,
  }
}

function answerResult(overrides: Partial<AnswerResult> = {}): AnswerResult {
  return {
    question_id: 'q1',
    question_index: 0,
    is_correct: true,
    points_earned: 1,
    max_points: 1,
    requires_manual_review: false,
    session_status: 'ACTIVE',
    current_index: 1,
    total_questions: 3,
    question: Q2,
    submitted_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.mocked(submitAnswer).mockReset()
})

describe('TestRunner', () => {
  it('renders the first question with server-indexed progress and a submit button', () => {
    render(<TestRunner session={session()} />)
    expect(screen.getByText('Capital of France?')).toBeInTheDocument()
    expect(screen.getByText('Question 1 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
  })

  it('labels a resumed session by the server question index, not the buffer position', () => {
    render(<TestRunner session={session({ current_index: 2, question: Q3 })} />)
    expect(screen.getByText('Largest planet?')).toBeInTheDocument()
    expect(screen.getByText('Question 3 of 3')).toBeInTheDocument()
  })

  it('rehydrates the current selection from draft_answers on resume', () => {
    render(<TestRunner session={session({ draft_answers: { q1: [1] } })} />)
    expect(screen.getByRole('radio', { name: 'Paris' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Lyon' })).not.toBeChecked()
  })

  it('dispatches on question.type: radios for mcq, checkboxes for multi', () => {
    const { unmount } = render(<TestRunner session={session()} />)
    expect(screen.getAllByRole('radio')).toHaveLength(2)
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    unmount()

    render(<TestRunner session={session({ question: Q2, current_index: 1 })} />)
    expect(screen.getAllByRole('checkbox')).toHaveLength(3)
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })

  it('submits the current answer, appends the next question, and advances', async () => {
    vi.mocked(submitAnswer).mockResolvedValue(answerResult())
    render(<TestRunner session={session()} />)

    fireEvent.click(screen.getByRole('radio', { name: 'Paris' }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })

    expect(submitAnswer).toHaveBeenCalledWith('s1', [1], 'q1', expect.any(String))
    expect(await screen.findByText('Which are prime?')).toBeInTheDocument()
    expect(screen.getByText('Question 2 of 3')).toBeInTheDocument()
  })

  it('shows the confirmation panel when the final answer is submitted', async () => {
    vi.mocked(submitAnswer).mockResolvedValue(
      answerResult({ question: null, session_status: 'SUBMITTED', question_index: 0 })
    )
    render(<TestRunner session={session({ total_questions: 1 })} />)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })

    expect(await screen.findByText('Quiz submitted')).toBeInTheDocument()
    expect(screen.queryByText('Capital of France?')).not.toBeInTheDocument()
  })

  it('locks inputs and the submit button optimistically while submitting', async () => {
    let resolve: (r: AnswerResult) => void = () => {}
    vi.mocked(submitAnswer).mockReturnValue(
      new Promise<AnswerResult>((res) => {
        resolve = res
      })
    )
    render(<TestRunner session={session()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Submit' }))

    expect(screen.getByRole('radio', { name: 'Paris' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Submitting…' })).toBeDisabled()

    await act(async () => {
      resolve(answerResult())
    })
  })

  it('surfaces a semantic error in an alert and keeps inputs locked', async () => {
    vi.mocked(submitAnswer).mockRejectedValue(new ApiError(409, 'Conflict', ''))
    render(<TestRunner session={session()} />)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/ended/i)
    expect(screen.getByRole('radio', { name: 'Paris' })).toBeDisabled()
  })

  it('recovers from a failed submit: the button becomes "Try again" and a retry advances', async () => {
    vi.mocked(submitAnswer)
      .mockRejectedValueOnce(new ApiError(500, 'Server Error', ''))
      .mockResolvedValueOnce(answerResult())
    render(<TestRunner session={session()} />)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })
    // Not bricked: a Try again control exists and is enabled.
    const retry = await screen.findByRole('button', { name: 'Try again' })
    expect(retry).toBeEnabled()

    await act(async () => {
      fireEvent.click(retry)
    })
    // Retry succeeded → advanced to the next question, error cleared.
    expect(await screen.findByText('Which are prime?')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('reuses the same idempotency key when retrying the same question', async () => {
    vi.mocked(submitAnswer)
      .mockRejectedValueOnce(new ApiError(500, 'Server Error', ''))
      .mockResolvedValueOnce(answerResult())
    render(<TestRunner session={session()} />)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })
    await act(async () => {
      fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    })

    const firstKey = vi.mocked(submitAnswer).mock.calls[0][3]
    const retryKey = vi.mocked(submitAnswer).mock.calls[1][3]
    expect(retryKey).toBe(firstKey)
  })

  // C1 probe: two synchronous entries into handleSubmit (rapid double-click)
  // must not fire two submits / append the next question twice.
  it('does not double-submit on a rapid double Submit click', async () => {
    vi.mocked(submitAnswer).mockResolvedValue(answerResult())
    render(<TestRunner session={session()} />)
    const btn = screen.getByRole('button', { name: 'Submit' })
    await act(async () => {
      fireEvent.click(btn)
      fireEvent.click(btn)
    })
    expect(submitAnswer).toHaveBeenCalledTimes(1)
    // Q2 must appear exactly once (no duplicate append).
    expect(screen.getAllByText('Which are prime?')).toHaveLength(1)
  })

  // C1 probe (the sharper trigger): a still-pending submit, then a second click
  // landing before the optimistic lock commits.
  it('ignores a second Submit click while the first is still in flight', async () => {
    let resolve: (r: AnswerResult) => void = () => {}
    vi.mocked(submitAnswer).mockReturnValue(
      new Promise<AnswerResult>((res) => {
        resolve = res
      })
    )
    render(<TestRunner session={session()} />)
    const btn = screen.getByRole('button', { name: 'Submit' })
    await act(async () => {
      fireEvent.click(btn)
      fireEvent.click(btn)
    })
    expect(submitAnswer).toHaveBeenCalledTimes(1)
    await act(async () => {
      resolve(answerResult())
    })
  })

  // C3: a null next question without a SUBMITTED status is a broken contract.
  // It must surface as a recoverable error, not silently soft-lock the shell.
  it('surfaces a recoverable error when a non-final answer returns no next question', async () => {
    vi.mocked(submitAnswer).mockResolvedValue(
      answerResult({ question: null, session_status: 'ACTIVE' })
    )
    render(<TestRunner session={session()} />)
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    // Recoverable, not stuck: a Try again control exists and is enabled.
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
    // Did not falsely show the submitted confirmation.
    expect(screen.queryByText('Quiz submitted')).not.toBeInTheDocument()
  })

  it('lets the participant review a prior answer read-only and return forward', async () => {
    vi.mocked(submitAnswer).mockResolvedValue(answerResult())
    render(<TestRunner session={session()} />)

    fireEvent.click(screen.getByRole('radio', { name: 'Paris' }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
    })
    expect(await screen.findByText('Which are prime?')).toBeInTheDocument()

    // Back to the answered Q1 — read-only, with its selection preserved.
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByText('Capital of France?')).toBeInTheDocument()
    const paris = screen.getByRole('radio', { name: 'Paris' })
    expect(paris).toBeChecked()
    expect(paris).toBeDisabled()

    // Forward again to the frontier.
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Which are prime?')).toBeInTheDocument()
  })
})
