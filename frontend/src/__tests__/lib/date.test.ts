import { describe, expect, it } from 'vitest'

import {
  formatDateTime,
  formatDueDate,
  formatTableDate,
  formatTimestamp,
  isDateFuture,
  isDatePast,
} from '@/lib/utils/date'

describe('formatDateTime', () => {
  it('returns — for null', () => {
    expect(formatDateTime(null)).toBe('—')
  })

  it('returns — for undefined', () => {
    expect(formatDateTime(undefined)).toBe('—')
  })

  it('returns a non-empty string for a valid ISO date', () => {
    const result = formatDateTime('2024-11-05T14:30:00Z')
    expect(result).not.toBe('—')
    expect(typeof result).toBe('string')
  })

  it('omits time when includeTime is false', () => {
    expect(formatDateTime('2024-11-05T00:00:00Z', false)).not.toContain('at')
  })
})

describe('formatTableDate', () => {
  it('returns — for null', () => {
    expect(formatTableDate(null)).toBe('—')
  })

  it('returns — for undefined', () => {
    expect(formatTableDate(undefined)).toBe('—')
  })

  it('returns a non-empty string for a valid date', () => {
    expect(formatTableDate('2024-11-05T14:30:00Z')).not.toBe('—')
  })
})

describe('formatTimestamp', () => {
  it('returns — for null', () => {
    expect(formatTimestamp(null)).toBe('—')
  })

  it('returns — for undefined', () => {
    expect(formatTimestamp(undefined)).toBe('—')
  })

  it('returns a non-empty string for a valid date', () => {
    expect(formatTimestamp('2024-11-05T14:30:00Z')).not.toBe('—')
  })
})

describe('isDatePast', () => {
  it('returns false for null', () => {
    expect(isDatePast(null)).toBe(false)
  })

  it('returns false for undefined', () => {
    expect(isDatePast(undefined)).toBe(false)
  })

  it('returns true for a past date', () => {
    expect(isDatePast('2020-01-01T00:00:00Z')).toBe(true)
  })

  it('returns false for a future date', () => {
    expect(isDatePast('2099-01-01T00:00:00Z')).toBe(false)
  })
})

describe('isDateFuture', () => {
  it('returns false for null', () => {
    expect(isDateFuture(null)).toBe(false)
  })

  it('returns false for undefined', () => {
    expect(isDateFuture(undefined)).toBe(false)
  })

  it('returns false for a past date', () => {
    expect(isDateFuture('2020-01-01T00:00:00Z')).toBe(false)
  })

  it('returns true for a future date', () => {
    expect(isDateFuture('2099-01-01T00:00:00Z')).toBe(true)
  })
})

describe('formatDueDate', () => {
  it('returns no-due-date defaults for null', () => {
    const result = formatDueDate(null)
    expect(result.formatted).toBe('No due date')
    expect(result.status).toBe('none')
    expect(result.isOverdue).toBe(false)
    expect(result.isUrgent).toBe(false)
  })

  it('marks a past date as overdue', () => {
    const result = formatDueDate('2020-01-01T00:00:00Z')
    expect(result.isOverdue).toBe(true)
    expect(result.status).toBe('overdue')
  })

  it('marks a far-future date as upcoming', () => {
    const result = formatDueDate('2099-01-01T00:00:00Z')
    expect(result.isOverdue).toBe(false)
    expect(result.status).toBe('upcoming')
  })
})
