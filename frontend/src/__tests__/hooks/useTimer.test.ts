import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useTimer } from '@/lib/hooks/useTimer'

vi.mock('sonner', () => ({
  toast: { warning: vi.fn() },
}))

import { toast } from 'sonner'

const TEST_ID = 'test-42'
const STORAGE_KEY = `quiz-timer-${TEST_ID}`

function renderTimer(overrides: Partial<Parameters<typeof useTimer>[0]> = {}) {
  const onTimeExpired = vi.fn()
  const result = renderHook(() =>
    useTimer({
      durationSeconds: 600,
      testId: TEST_ID,
      onTimeExpired,
      ...overrides,
    }),
  )
  return { ...result, onTimeExpired }
}

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
  vi.clearAllMocks()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useTimer', () => {
  it('starts at the full duration and counts down each second', () => {
    const { result } = renderTimer()

    expect(result.current.timeRemaining).toBe(600)

    act(() => vi.advanceTimersByTime(3000))
    expect(result.current.timeRemaining).toBe(597)
  })

  it('formats remaining time as MM:SS', () => {
    const { result } = renderTimer({ durationSeconds: 125 })

    expect(result.current.formatTime()).toBe('02:05')

    act(() => vi.advanceTimersByTime(6000))
    expect(result.current.formatTime()).toBe('01:59')
  })

  it('does not start when autoStart is false until resumed', () => {
    const { result } = renderTimer({ autoStart: false })

    act(() => vi.advanceTimersByTime(5000))
    expect(result.current.timeRemaining).toBe(600)

    act(() => result.current.resume())
    act(() => vi.advanceTimersByTime(2000))
    expect(result.current.timeRemaining).toBe(598)
  })

  it('pause stops the countdown and resume continues it', () => {
    const { result } = renderTimer()

    act(() => vi.advanceTimersByTime(2000))
    act(() => result.current.pause())
    act(() => vi.advanceTimersByTime(10_000))
    expect(result.current.timeRemaining).toBe(598) // unchanged while paused

    act(() => result.current.resume())
    act(() => vi.advanceTimersByTime(1000))
    expect(result.current.timeRemaining).toBe(597)
  })

  it('expires at zero and fires onTimeExpired exactly once', () => {
    const { result, onTimeExpired } = renderTimer({ durationSeconds: 2 })

    act(() => vi.advanceTimersByTime(2000)) // reach 0
    expect(result.current.timeRemaining).toBe(0)
    expect(result.current.isExpired).toBe(true)

    act(() => vi.advanceTimersByTime(200)) // callback fires after 100ms delay
    expect(onTimeExpired).toHaveBeenCalledTimes(1)

    act(() => vi.advanceTimersByTime(5000)) // no repeat firing
    expect(onTimeExpired).toHaveBeenCalledTimes(1)
  })

  it('cannot be resumed after expiry', () => {
    const { result } = renderTimer({ durationSeconds: 1 })

    act(() => vi.advanceTimersByTime(1100))
    expect(result.current.isExpired).toBe(true)

    act(() => result.current.resume())
    act(() => vi.advanceTimersByTime(3000))
    expect(result.current.timeRemaining).toBe(0)
    expect(result.current.isExpired).toBe(true)
  })

  it('fires each warning exactly once as the 5- and 1-minute thresholds are crossed', () => {
    const { result } = renderTimer({ durationSeconds: 302 })

    expect(result.current.isWarning).toBe(false)

    act(() => vi.advanceTimersByTime(2000)) // 300s left — crosses 5-minute mark
    expect(result.current.isWarning).toBe(true)
    expect(result.current.isCritical).toBe(false)
    expect(toast.warning).toHaveBeenCalledWith(
      '5 Minutes Remaining',
      expect.objectContaining({ description: expect.any(String) }),
    )
    expect(toast.warning).toHaveBeenCalledTimes(1)

    // staying under 5 minutes must not re-fire the warning every tick
    act(() => vi.advanceTimersByTime(5000)) // 295s left
    expect(toast.warning).toHaveBeenCalledTimes(1)

    act(() => vi.advanceTimersByTime(235_000)) // 60s left — crosses 1-minute mark
    expect(result.current.isCritical).toBe(true)
    expect(toast.warning).toHaveBeenCalledWith(
      '1 Minute Remaining!',
      expect.objectContaining({ description: expect.any(String) }),
    )
    expect(toast.warning).toHaveBeenCalledTimes(2)

    // the 1-minute warning likewise fires once, not on every subsequent second
    act(() => vi.advanceTimersByTime(5000)) // 55s left
    expect(toast.warning).toHaveBeenCalledTimes(2)
  })

  it('persists remaining time to localStorage on each tick', () => {
    renderTimer()

    act(() => vi.advanceTimersByTime(2000))

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    expect(stored.timeRemaining).toBe(598)
  })

  it('restores remaining time from localStorage, subtracting elapsed wall time', () => {
    vi.setSystemTime(new Date('2026-06-06T12:00:00Z'))
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        timeRemaining: 50,
        timestamp: Date.now() - 10_000, // saved 10s ago
      }),
    )

    const { result } = renderTimer()
    expect(result.current.timeRemaining).toBe(40)
  })

  it('finalizes expiry when the stored time has already fully elapsed on hydration', () => {
    vi.setSystemTime(new Date('2026-06-06T12:00:00Z'))
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        timeRemaining: 20,
        timestamp: Date.now() - 30_000, // saved 30s ago — the 20s budget is gone
      }),
    )

    const { result, onTimeExpired } = renderTimer()

    // Hydrated value is immediately clamped to 0 and storage cleared...
    expect(result.current.timeRemaining).toBe(0)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()

    // ...and expiry finalization is flushed on the next tick (deferred state).
    act(() => vi.advanceTimersByTime(0))
    expect(result.current.isExpired).toBe(true)
    expect(onTimeExpired).toHaveBeenCalledTimes(1)
  })

  it('clears localStorage when the timer expires', () => {
    renderTimer({ durationSeconds: 1 })

    act(() => vi.advanceTimersByTime(1100))
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('reset restores the original duration and re-arms expiry', () => {
    const { result, onTimeExpired } = renderTimer({ durationSeconds: 2 })

    act(() => vi.advanceTimersByTime(2000)) // reach 0
    act(() => vi.advanceTimersByTime(200)) // expiry callback fires after 100ms delay
    expect(onTimeExpired).toHaveBeenCalledTimes(1)

    act(() => result.current.reset())
    expect(result.current.timeRemaining).toBe(2)
    expect(result.current.isExpired).toBe(false)

    act(() => vi.advanceTimersByTime(2000)) // expire again after reset
    act(() => vi.advanceTimersByTime(200))
    expect(onTimeExpired).toHaveBeenCalledTimes(2)
  })

  it('reset accepts an override duration', () => {
    const { result } = renderTimer({ durationSeconds: 600 })

    act(() => result.current.reset(120))
    expect(result.current.timeRemaining).toBe(120)
    expect(result.current.formatTime()).toBe('02:00')
  })
})
