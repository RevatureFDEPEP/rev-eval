import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { MultiSelectQuestion } from '@/components/quiz/MultiSelectQuestion'
import { ParticipantQuestion } from '@/lib/api/types'

const QUESTION: ParticipantQuestion = {
  id: 'q2',
  type: 'multi',
  question_text: 'Which are prime?',
  options: [
    { option_id: 10, text: 'Two' },
    { option_id: 11, text: 'Four' },
    { option_id: 12, text: 'Three' },
  ],
  index: 0,
}

describe('MultiSelectQuestion', () => {
  it('renders all options as checkboxes', () => {
    render(<MultiSelectQuestion question={QUESTION} selected={[]} onChange={vi.fn()} />)
    expect(screen.getAllByRole('checkbox')).toHaveLength(3)
  })

  it('reflects the selected options', () => {
    render(<MultiSelectQuestion question={QUESTION} selected={[10, 12]} onChange={vi.fn()} />)
    expect(screen.getByRole('checkbox', { name: 'Two' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Three' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Four' })).not.toBeChecked()
  })

  it('adds an option_id when checking', () => {
    const onChange = vi.fn()
    render(<MultiSelectQuestion question={QUESTION} selected={[10]} onChange={onChange} />)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Three' }))
    expect(onChange).toHaveBeenCalledWith([10, 12])
  })

  it('removes an option_id when unchecking', () => {
    const onChange = vi.fn()
    render(<MultiSelectQuestion question={QUESTION} selected={[10, 12]} onChange={onChange} />)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Two' }))
    expect(onChange).toHaveBeenCalledWith([12])
  })
})
