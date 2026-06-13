import { describe, expect, it } from 'vitest'

import { examReducer, initialExamState } from '@/lib/exam/examReducer'
import type { AnswerResult } from '@/lib/api/types'

function result(overrides: Partial<AnswerResult> = {}): AnswerResult {
  return {
    question_id: 'q0',
    question_index: 0,
    is_correct: true,
    points_earned: 1,
    max_points: 1,
    requires_manual_review: false,
    session_status: 'ACTIVE',
    current_index: 1,
    total_questions: 3,
    question: null,
    submitted_at: null,
    ...overrides,
  }
}

const submitting = { ...initialExamState, status: 'submitting' as const }

describe('examReducer', () => {
  it('SUBMIT_START moves to submitting (optimistic lock) and clears any error', () => {
    const s = examReducer(initialExamState, { type: 'SUBMIT_START' })
    expect(s.status).toBe('submitting')
    expect(s.error).toBeNull()
  })

  it('SUBMIT_CONFIRMED with more questions returns to active and records the answered index', () => {
    const s = examReducer(submitting, {
      type: 'SUBMIT_CONFIRMED',
      result: result({ question_index: 0, session_status: 'ACTIVE' }),
    })
    expect(s.status).toBe('active')
    expect(s.answeredIndices.has(0)).toBe(true)
  })

  it('SUBMIT_CONFIRMED with SUBMITTED finishes the exam', () => {
    const s = examReducer(submitting, {
      type: 'SUBMIT_CONFIRMED',
      result: result({ question_index: 2, session_status: 'SUBMITTED' }),
    })
    expect(s.status).toBe('submitted')
    expect(s.answeredIndices.has(2)).toBe(true)
  })

  it('SUBMIT_FAILED moves to error and surfaces the message', () => {
    const s = examReducer(submitting, { type: 'SUBMIT_FAILED', error: 'boom' })
    expect(s.status).toBe('error')
    expect(s.error).toBe('boom')
  })

  it('SUBMIT_START from error retries (clears error, back to submitting)', () => {
    const errored = { ...initialExamState, status: 'error' as const, error: 'boom' }
    const s = examReducer(errored, { type: 'SUBMIT_START' })
    expect(s.status).toBe('submitting')
    expect(s.error).toBeNull()
  })

  it('does not mutate the previous answeredIndices set', () => {
    const s = examReducer(submitting, {
      type: 'SUBMIT_CONFIRMED',
      result: result({ question_index: 0 }),
    })
    expect(submitting.answeredIndices.has(0)).toBe(false)
    expect(s.answeredIndices).not.toBe(submitting.answeredIndices)
  })
})
