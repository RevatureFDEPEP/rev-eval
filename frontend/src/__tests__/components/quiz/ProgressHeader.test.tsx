import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProgressHeader } from '@/components/quiz/ProgressHeader'

const DEFAULT_PROPS = {
  part: 'A' as const,
  currentQuestionNumber: 1,
  answeredCount: 0,
  totalQuestions: 10,
  testName: 'Java Fundamentals',
  onPrevious: jest.fn(),
  onNext: jest.fn(),
  hasPrevious: false,
  hasNext: true,
}

describe('ProgressHeader', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders the test name', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} />)
    expect(screen.getByText('Java Fundamentals')).toBeInTheDocument()
  })

  it('shows the correct Part badge', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} />)
    expect(screen.getByText('Part A')).toBeInTheDocument()
  })

  it('shows Part B badge when part=B', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} part="B" />)
    expect(screen.getByText('Part B')).toBeInTheDocument()
  })

  it('displays current question number and total', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} />)
    expect(screen.getByText(/Question 1 of 10/)).toBeInTheDocument()
  })

  it('shows answered count and percentage', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} answeredCount={5} />)
    expect(screen.getByText(/Answered 5\/10/)).toBeInTheDocument()
    expect(screen.getByText(/50% complete/)).toBeInTheDocument()
  })

  it('disables Previous button when hasPrevious is false', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} hasPrevious={false} />)
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()
  })

  it('disables Next button when hasNext is false', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} hasNext={false} />)
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled()
  })

  it('enables Previous button when hasPrevious is true', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} hasPrevious={true} />)
    expect(screen.getByRole('button', { name: /previous/i })).not.toBeDisabled()
  })

  it('calls onNext when Next button is clicked', async () => {
    const user = userEvent.setup()
    const onNext = jest.fn()
    render(<ProgressHeader {...DEFAULT_PROPS} onNext={onNext} hasNext={true} />)
    await user.click(screen.getByRole('button', { name: /next/i }))
    expect(onNext).toHaveBeenCalledTimes(1)
  })

  it('calls onPrevious when Previous button is clicked', async () => {
    const user = userEvent.setup()
    const onPrevious = jest.fn()
    render(<ProgressHeader {...DEFAULT_PROPS} onPrevious={onPrevious} hasPrevious={true} />)
    await user.click(screen.getByRole('button', { name: /previous/i }))
    expect(onPrevious).toHaveBeenCalledTimes(1)
  })

  it('renders testRole badge when provided', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} testRole="Java Developer" />)
    expect(screen.getByText('Java Developer')).toBeInTheDocument()
  })

  it('does not render testRole badge when omitted', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} />)
    expect(screen.queryByText('Java Developer')).not.toBeInTheDocument()
  })

  it('uses overallQuestionCount as denominator when provided', () => {
    render(<ProgressHeader {...DEFAULT_PROPS} answeredCount={10} totalQuestions={10} overallQuestionCount={20} />)
    expect(screen.getByText(/Answered 10\/20/)).toBeInTheDocument()
    expect(screen.getByText(/50% complete/)).toBeInTheDocument()
  })
})
