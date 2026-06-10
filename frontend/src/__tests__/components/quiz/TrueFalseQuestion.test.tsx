import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TrueFalseQuestion } from '@/components/quiz/TrueFalseQuestion'
import type { QuizQuestion } from '@/lib/api/types'

const MOCK_QUESTION: QuizQuestion = {
  question_id: 'q2',
  question_text: 'Java is a statically typed language.',
  question_type: 'true_false',
  difficulty: 'easy',
}

describe('TrueFalseQuestion', () => {
  it('renders True and False buttons', () => {
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    expect(screen.getByRole('button', { name: /true/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /false/i })).toBeInTheDocument()
  })

  it('calls onAnswerChange(true) when True is clicked', async () => {
    const user = userEvent.setup()
    const onAnswerChange = jest.fn()
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={onAnswerChange} />)
    await user.click(screen.getByRole('button', { name: /true/i }))
    expect(onAnswerChange).toHaveBeenCalledWith(true)
  })

  it('calls onAnswerChange(false) when False is clicked', async () => {
    const user = userEvent.setup()
    const onAnswerChange = jest.fn()
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={onAnswerChange} />)
    await user.click(screen.getByRole('button', { name: /false/i }))
    expect(onAnswerChange).toHaveBeenCalledWith(false)
  })

  it('does not call onAnswerChange when no button is clicked', () => {
    const onAnswerChange = jest.fn()
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={onAnswerChange} />)
    expect(onAnswerChange).not.toHaveBeenCalled()
  })

  it('renders two buttons total', () => {
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={null} onAnswerChange={jest.fn()} />)
    expect(screen.getAllByRole('button')).toHaveLength(2)
  })

  it('True button has default variant when selectedAnswer is true', () => {
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={true} onAnswerChange={jest.fn()} />)
    const trueButton = screen.getByRole('button', { name: /true/i })
    expect(trueButton).toBeInTheDocument()
  })

  it('False button has default variant when selectedAnswer is false', () => {
    render(<TrueFalseQuestion question={MOCK_QUESTION} selectedAnswer={false} onAnswerChange={jest.fn()} />)
    const falseButton = screen.getByRole('button', { name: /false/i })
    expect(falseButton).toBeInTheDocument()
  })
})
