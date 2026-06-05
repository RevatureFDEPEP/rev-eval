import {
  formatDateTime,
  formatTableDate,
  formatRelativeTime,
  formatDueDate,
  formatTimestamp,
  isDatePast,
  isDateFuture,
} from '@/lib/utils/date'

const PAST_ISO = '2020-01-15T10:00:00Z'
const FUTURE_ISO = '2099-06-01T12:00:00Z'

describe('formatDateTime', () => {
  it('returns em dash for null', () => {
    expect(formatDateTime(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatDateTime(undefined)).toBe('—')
  })

  it('includes month/day/year in output', () => {
    const result = formatDateTime(PAST_ISO)
    expect(result).toMatch(/Jan 15, 2020/)
  })

  it('omits time when includeTime=false', () => {
    const result = formatDateTime(PAST_ISO, false)
    expect(result).toBe('Jan 15, 2020')
  })

  it('accepts a Date object', () => {
    const result = formatDateTime(new Date('2020-01-15T14:00:00Z'), false)
    expect(result).toMatch(/Jan 15, 2020/)
  })

  it('handles date-only strings (normalised to start-of-day UTC)', () => {
    const result = formatDateTime('2020-01-15', false)
    // The function appends T00:00:00Z; the displayed day depends on local TZ.
    // Assert the year is correct regardless of TZ offset.
    expect(result).toMatch(/2020/)
  })
})

describe('formatTableDate', () => {
  it('returns em dash for null', () => {
    expect(formatTableDate(null)).toBe('—')
  })

  it('formats compactly with M/d/yy pattern', () => {
    const result = formatTableDate(PAST_ISO)
    expect(result).toMatch(/1\/15\/20/)
  })
})

describe('formatRelativeTime', () => {
  it('returns em dash for null', () => {
    expect(formatRelativeTime(null)).toBe('—')
  })

  it('returns a string containing "ago" for past dates', () => {
    expect(formatRelativeTime(PAST_ISO)).toContain('ago')
  })

  it('returns a string containing "in" for future dates', () => {
    expect(formatRelativeTime(FUTURE_ISO)).toMatch(/^in /)
  })
})

describe('formatDueDate', () => {
  it('returns no-due-date shape for null', () => {
    const result = formatDueDate(null)
    expect(result.formatted).toBe('No due date')
    expect(result.status).toBe('none')
    expect(result.isOverdue).toBe(false)
    expect(result.isUrgent).toBe(false)
  })

  it('marks past dates as overdue', () => {
    const result = formatDueDate(PAST_ISO)
    expect(result.isOverdue).toBe(true)
    expect(result.status).toBe('overdue')
  })

  it('marks far-future dates as upcoming', () => {
    const result = formatDueDate(FUTURE_ISO)
    expect(result.isOverdue).toBe(false)
    expect(result.isUrgent).toBe(false)
    expect(result.status).toBe('upcoming')
  })
})

describe('formatTimestamp', () => {
  it('returns em dash for null', () => {
    expect(formatTimestamp(null)).toBe('—')
  })

  it('includes full month name', () => {
    expect(formatTimestamp(PAST_ISO)).toMatch(/January 15, 2020/)
  })
})

describe('isDatePast', () => {
  it('returns false for null', () => {
    expect(isDatePast(null)).toBe(false)
  })

  it('returns true for a past date', () => {
    expect(isDatePast(PAST_ISO)).toBe(true)
  })

  it('returns false for a future date', () => {
    expect(isDatePast(FUTURE_ISO)).toBe(false)
  })
})

describe('isDateFuture', () => {
  it('returns false for null', () => {
    expect(isDateFuture(null)).toBe(false)
  })

  it('returns true for a future date', () => {
    expect(isDateFuture(FUTURE_ISO)).toBe(true)
  })

  it('returns false for a past date', () => {
    expect(isDateFuture(PAST_ISO)).toBe(false)
  })
})
