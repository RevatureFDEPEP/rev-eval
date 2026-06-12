import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SingleSelectQuestion } from '@/components/quiz/SingleSelectQuestion'
import { ParticipantQuestion } from '@/lib/api/types'

const QUESTION: ParticipantQuestion = {
  id: 'q1',
  type: 'mcq',
  question_text: 'Capital of France?',
  options: [
    { option_id: 1, text: 'Paris' },
    { option_id: 2, text: 'Lyon' },
  ],
  index: 0,
}

describe('SingleSelectQuestion', () => {
  it('renders all options as radios', () => {
    render(<SingleSelectQuestion question={QUESTION} selected={[]} onChange={vi.fn()} />)
    expect(screen.getAllByRole('radio')).toHaveLength(2)
  })

  it('reflects the selected option', () => {
    render(<SingleSelectQuestion question={QUESTION} selected={[2]} onChange={vi.fn()} />)
    expect(screen.getByRole('radio', { name: 'Lyon' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Paris' })).not.toBeChecked()
  })

  it('calls onChange with a one-element array on selection', () => {
    const onChange = vi.fn()
    render(<SingleSelectQuestion question={QUESTION} selected={[]} onChange={onChange} />)
    fireEvent.click(screen.getByRole('radio', { name: 'Paris' }))
    expect(onChange).toHaveBeenCalledWith([1])
  })

  it('shows an error when options are missing', () => {
    render(
      <SingleSelectQuestion
        question={{ ...QUESTION, options: undefined }}
        selected={[]}
        onChange={vi.fn()}
      />
    )
    expect(screen.getByText(/no options available/i)).toBeInTheDocument()
  })
})
