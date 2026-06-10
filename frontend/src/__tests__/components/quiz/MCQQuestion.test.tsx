import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MCQQuestion } from '@/components/quiz/MCQQuestion'
import type { QuizQuestion } from '@/lib/api/types'

const MOCK_QUESTION: QuizQuestion = {
  question_id: 'q1',
  question_text: 'What is the purpose of Java interfaces?',
  question_type: 'mcq',
  difficulty: 'easy',
  options: [
    { option_id: 1, text: 'Define contracts for classes' },
    { option_id: 2, text: 'Store data persistently' },
    { option_id: 3, text: 'Replace abstract classes entirely' },
  ],
}

describe('MCQQuestion', () => {
  it('renders all option labels', () => {
    render(<MCQQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    expect(screen.getByText('Define contracts for classes')).toBeInTheDocument()
    expect(screen.getByText('Store data persistently')).toBeInTheDocument()
    expect(screen.getByText('Replace abstract classes entirely')).toBeInTheDocument()
  })

  it('shows error message when options array is empty', () => {
    const noOpts = { ...MOCK_QUESTION, options: [] }
    render(<MCQQuestion question={noOpts} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    expect(screen.getByText(/No options available/)).toBeInTheDocument()
  })

  it('shows error message when options is undefined', () => {
    const noOpts = { ...MOCK_QUESTION, options: undefined }
    render(<MCQQuestion question={noOpts} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    expect(screen.getByText(/No options available/)).toBeInTheDocument()
  })

  it('renders one radio button per option', () => {
    render(<MCQQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(3)
  })

  it('calls onAnswerChange with option_id when a radio is clicked', async () => {
    const user = userEvent.setup()
    const onAnswerChange = jest.fn()
    render(<MCQQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={onAnswerChange} />)
    await user.click(screen.getByRole('radio', { name: /Define contracts for classes/ }))
    expect(onAnswerChange).toHaveBeenCalledWith(1)
  })

  it('marks the currently selected option as checked', () => {
    render(<MCQQuestion question={MOCK_QUESTION} selectedAnswer={2} onAnswerChange={jest.fn()} />)
    const selected = screen.getByRole('radio', { name: /Store data persistently/ })
    expect(selected).toHaveAttribute('data-state', 'checked')
  })

  it('leaves all options unchecked when selectedAnswer is null', () => {
    render(<MCQQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    const radios = screen.getAllByRole('radio')
    radios.forEach((radio) => {
      expect(radio).toHaveAttribute('data-state', 'unchecked')
    })
  })
})
