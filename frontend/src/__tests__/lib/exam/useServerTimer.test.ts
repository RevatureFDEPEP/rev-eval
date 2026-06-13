import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useServerTimer } from '@/lib/exam/useServerTimer'

beforeEach(() => {
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

describe('useServerTimer', () => {
  it('counts down from the server-derived remaining', () => {
    vi.setSystemTime(new Date('2026-06-12T10:00:00Z'))
    const { result } = renderHook(() =>
      useServerTimer('2026-06-12T10:00:00Z', '2026-06-12T10:01:00Z', () => {})
    )
    expect(result.current.timeRemaining).toBe(60)
    act(() => {
      vi.advanceTimersByTime(10_000)
    })
    expect(result.current.timeRemaining).toBe(50)
  })

  it('absorbs client clock skew (uses the server delta, not the local clock)', () => {
    // Local clock is years off; remaining is still expires_at − server_now.
    vi.setSystemTime(new Date('2030-01-01T00:00:00Z'))
    const { result } = renderHook(() =>
      useServerTimer('2026-06-12T10:00:00Z', '2026-06-12T10:05:00Z', () => {})
    )
    expect(result.current.timeRemaining).toBe(300)
  })

  it('fires onExpire exactly once when it reaches zero', () => {
    vi.setSystemTime(new Date('2026-06-12T10:00:00Z'))
    const onExpire = vi.fn()
    renderHook(() =>
      useServerTimer('2026-06-12T10:00:00Z', '2026-06-12T10:00:03Z', onExpire)
    )
    act(() => {
      vi.advanceTimersByTime(6_000) // well past zero — must not fire repeatedly
    })
    expect(onExpire).toHaveBeenCalledTimes(1)
  })

  it('re-fires onExpire after being re-enabled while still past expiry', () => {
    // Models a submit that advanced the session (status active→submitting→active)
    // while the clock was already at zero: the timer must fire again, not freeze.
    vi.setSystemTime(new Date('2026-06-12T10:00:00Z'))
    const onExpire = vi.fn()
    const { rerender } = renderHook(
      ({ enabled }) =>
        useServerTimer(
          '2026-06-12T10:00:00Z',
          '2026-06-12T10:00:03Z',
          onExpire,
          enabled
        ),
      { initialProps: { enabled: true } }
    )
    act(() => {
      vi.advanceTimersByTime(5_000)
    })
    expect(onExpire).toHaveBeenCalledTimes(1)

    // Pause (submitting) then re-enable (back to active) — still past expiry.
    rerender({ enabled: false })
    rerender({ enabled: true })
    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    expect(onExpire).toHaveBeenCalledTimes(2)
  })

  it('does not run while disabled (locked)', () => {
    vi.setSystemTime(new Date('2026-06-12T10:00:00Z'))
    const onExpire = vi.fn()
    renderHook(() =>
      useServerTimer('2026-06-12T10:00:00Z', '2026-06-12T10:00:03Z', onExpire, false)
    )
    act(() => {
      vi.advanceTimersByTime(6_000)
    })
    expect(onExpire).not.toHaveBeenCalled()
  })

  it('formats remaining time as m:ss', () => {
    vi.setSystemTime(new Date('2026-06-12T10:00:00Z'))
    const { result } = renderHook(() =>
      useServerTimer('2026-06-12T10:00:00Z', '2026-06-12T10:01:05Z', () => {})
    )
    expect(result.current.formatTime()).toBe('1:05')
  })
})
