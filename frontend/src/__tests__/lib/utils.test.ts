import { cn } from '@/lib/utils'

describe('cn', () => {
  it('returns a single class unchanged', () => {
    expect(cn('foo')).toBe('foo')
  })

  it('merges multiple classes', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('drops falsy conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
  })

  it('resolves tailwind conflicts — last value wins', () => {
    expect(cn('p-4', 'p-8')).toBe('p-8')
  })

  it('handles undefined and null without throwing', () => {
    expect(cn('foo', undefined, null as never, 'bar')).toBe('foo bar')
  })

  it('returns empty string when called with no args', () => {
    expect(cn()).toBe('')
  })
})
