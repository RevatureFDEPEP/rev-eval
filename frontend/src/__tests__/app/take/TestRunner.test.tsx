import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TestRunner from '@/app/take/[testId]/TestRunner'
import type { SessionRead, AnswerResponse } from '@/lib/api/sessions'
import type { AuthUser } from '@/context/AuthContext'

// --- mocks ---
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('@/lib/api/sessions', () => ({
  submitAnswer: jest.fn(),
}))

import { submitAnswer } from '@/lib/api/sessions'
const mockSubmitAnswer = submitAnswer as jest.MockedFunction<typeof submitAnswer>

// --- fixtures ---
const MOCK_USER: AuthUser = { id: 1, email: 'test@example.com', role: 'participant' }

const Q1 = {
  question_id: 'q1',
  question_text: 'What does SQL stand for?',
  question_type: 'mcq' as const,
  difficulty: 'easy' as const,
  options: [
    { option_id: 1, text: 'Structured Query Language' },
    { option_id: 2, text: 'Simple Query Language' },
    { option_id: 3, text: 'Sequential Query Logic' },
  ],
}

const Q2 = {
  question_id: 'q2',
  question_text: 'Which keyword creates a table?',
  question_type: 'mcq' as const,
  difficulty: 'medium' as const,
  options: [
    { option_id: 1, text: 'CREATE' },
    { option_id: 2, text: 'MAKE' },
    { option_id: 3, text: 'BUILD' },
  ],
}

function makeSession(firstQuestion = Q1): SessionRead {
  return {
    session_id: 'sess-abc',
    session_token: 'tok-xyz',
    test_id: 10,
    user_id: 1,
    status: 'IN_PROGRESS',
    current_index: 0,
    server_now: '2026-06-18T00:00:00Z',
    expires_at: '2026-06-18T01:00:00Z',
    first_question: firstQuestion,
  }
}

function makeAnswerResponse(overrides: Partial<AnswerResponse> = {}): AnswerResponse {
  return {
    session_id: 'sess-abc',
    question_id: Q1.question_id,
    question_index: 0,
    score: 1.0,
    algorithm: 'exact',
    session_status: 'IN_PROGRESS',
    current_index: 1,
    next_question: Q2,
    ...overrides,
  }
}

beforeEach(() => {
  mockSubmitAnswer.mockReset()
})

describe('TestRunner', () => {
  it('renders the first question text', () => {
    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    expect(screen.getByText('What does SQL stand for?')).toBeInTheDocument()
  })

  it('Previous button is disabled on the first question', () => {
    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()
  })

  it('Next button is always present', () => {
    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
  })

  it('shows an empty-state card when first_question is null', () => {
    const noQ: SessionRead = { ...makeSession(), first_question: null }
    render(<TestRunner quizSession={noQ} user={MOCK_USER} />)
    expect(screen.getByText(/no questions available/i)).toBeInTheDocument()
  })

  it('selecting an MCQ option marks the radio as checked', async () => {
    const user = userEvent.setup()
    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)

    const radio = screen.getByRole('radio', { name: /Structured Query Language/i })
    await user.click(radio)
    expect(radio).toHaveAttribute('data-state', 'checked')
  })

  it('Next calls submitAnswer and renders the next question', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockResolvedValueOnce(makeAnswerResponse())

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)

    await user.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() =>
      expect(mockSubmitAnswer).toHaveBeenCalledWith(
        'sess-abc',
        Q1.question_id,
        expect.any(Array),
      ),
    )

    await waitFor(() =>
      expect(screen.getByText('Which keyword creates a table?')).toBeInTheDocument(),
    )
  })

  it('shows completed state when session_status is SUBMITTED', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockResolvedValueOnce(
      makeAnswerResponse({ session_status: 'SUBMITTED', next_question: null }),
    )

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    await user.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() =>
      expect(screen.getByText(/quiz submitted/i)).toBeInTheDocument(),
    )
  })

  it('displays an error banner when submitAnswer rejects', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockRejectedValueOnce(new Error('Network error'))

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    await user.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() =>
      expect(screen.getByText(/network error/i)).toBeInTheDocument(),
    )
  })

  it('Previous becomes enabled after advancing to the second question', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockResolvedValueOnce(makeAnswerResponse())

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    await user.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() =>
      expect(screen.getByText('Which keyword creates a table?')).toBeInTheDocument(),
    )

    expect(screen.getByRole('button', { name: /previous/i })).not.toBeDisabled()
  })

  it('navigating back shows the first question without an API call', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockResolvedValueOnce(makeAnswerResponse())

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    // Advance to Q2
    await user.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText('Which keyword creates a table?')).toBeInTheDocument(),
    )

    // Go back — must NOT call submitAnswer again
    await user.click(screen.getByRole('button', { name: /previous/i }))
    expect(screen.getByText('What does SQL stand for?')).toBeInTheDocument()
    expect(mockSubmitAnswer).toHaveBeenCalledTimes(1)
  })

  it('Next navigates to the cached question without another API call', async () => {
    const user = userEvent.setup()
    mockSubmitAnswer.mockResolvedValueOnce(makeAnswerResponse())

    render(<TestRunner quizSession={makeSession()} user={MOCK_USER} />)
    // Advance → Q2
    await user.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText('Which keyword creates a table?')).toBeInTheDocument(),
    )
    // Go back to Q1
    await user.click(screen.getByRole('button', { name: /previous/i }))
    expect(screen.getByText('What does SQL stand for?')).toBeInTheDocument()

    // Advance again — Q2 is already cached, no additional API call
    await user.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText('Which keyword creates a table?')).toBeInTheDocument(),
    )
    // Still only one API call total
    expect(mockSubmitAnswer).toHaveBeenCalledTimes(1)
  })
})
