import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TestRunner } from '@/components/quiz/TestRunner'
import { ParticipantQuestion, SessionResponse } from '@/lib/api/types'

const QUESTIONS: ParticipantQuestion[] = [
  {
    id: 'q1',
    type: 'mcq',
    question_text: 'Capital of France?',
    options: [
      { option_id: 1, text: 'Paris' },
      { option_id: 2, text: 'Lyon' },
    ],
    index: 0,
  },
  {
    id: 'q2',
    type: 'multi',
    question_text: 'Which are prime?',
    options: [
      { option_id: 10, text: 'Two' },
      { option_id: 11, text: 'Four' },
      { option_id: 12, text: 'Three' },
    ],
    index: 1,
  },
  {
    id: 'q3',
    type: 'mcq',
    question_text: 'Largest planet?',
    options: [
      { option_id: 20, text: 'Jupiter' },
      { option_id: 21, text: 'Mars' },
    ],
    index: 2,
  },
]

const SESSION: SessionResponse = {
  session_id: 's1',
  session_token: 'tok',
  status: 'ACTIVE',
  server_now: '2026-06-11T10:00:00',
  expires_at: '2026-06-11T10:30:00',
  total_questions: 5,
  current_index: 0,
  question: QUESTIONS[0],
}

function renderRunner() {
  return render(<TestRunner session={SESSION} initialQuestions={QUESTIONS} />)
}

describe('TestRunner', () => {
  it('renders the first question with progress', () => {
    renderRunner()
    expect(screen.getByText('Capital of France?')).toBeInTheDocument()
    expect(screen.getByText('Question 1 of 5')).toBeInTheDocument()
  })

  it('clamps navigation: Previous disabled first, Next disabled last', () => {
    renderRunner()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled()

    fireEvent.click(screen.getByRole('button', { name: 'Next' })) // -> Q2
    fireEvent.click(screen.getByRole('button', { name: 'Next' })) // -> Q3
    expect(screen.getByText('Question 3 of 5')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled()
  })

  it('hides navigation and shows total-scoped progress with a single buffered question', () => {
    // Production W3-F1 path: only the current question is seeded, while the
    // session reports the full exam length. Nav must not render a dead-end.
    render(<TestRunner session={SESSION} />)
    expect(screen.getByText('Question 1 of 5')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Previous' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument()
  })

  it('dispatches on question.type: radios for mcq, checkboxes for multi', () => {
    renderRunner()
    // Q1 is mcq -> radios
    expect(screen.getAllByRole('radio')).toHaveLength(2)
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' })) // -> Q2 (multi)
    expect(screen.getAllByRole('checkbox')).toHaveLength(3)
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })

  it('preserves a selection across forward and backward navigation', () => {
    renderRunner()
    // Select "Paris" on Q1
    fireEvent.click(screen.getByRole('radio', { name: 'Paris' }))
    expect(screen.getByRole('radio', { name: 'Paris' })).toBeChecked()

    // Navigate Q1 -> Q2 -> back to Q1
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Which are prime?')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))

    // Selection survived
    expect(screen.getByText('Capital of France?')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Paris' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Lyon' })).not.toBeChecked()
  })

  it('accumulates and removes multi-select toggles', () => {
    renderRunner()
    fireEvent.click(screen.getByRole('button', { name: 'Next' })) // -> Q2 (multi)

    fireEvent.click(screen.getByRole('checkbox', { name: 'Two' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Three' }))
    expect(screen.getByRole('checkbox', { name: 'Two' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Three' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Four' })).not.toBeChecked()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Two' })) // uncheck
    expect(screen.getByRole('checkbox', { name: 'Two' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Three' })).toBeChecked()
  })
})
