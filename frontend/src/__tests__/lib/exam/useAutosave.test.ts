import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api/sessions', () => ({
  saveDraft: vi.fn().mockResolvedValue({}),
}))

import { saveDraft } from '@/lib/api/sessions'
import { useAutosave } from '@/lib/exam/useAutosave'

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(saveDraft).mockClear()
})
afterEach(() => {
  vi.useRealTimers()
})

describe('useAutosave', () => {
  it('does not save before the 30s debounce elapses', () => {
    const answers = new Map([['q1', [1]]])
    renderHook(() => useAutosave('s1', answers, true))
    act(() => {
      vi.advanceTimersByTime(29_000)
    })
    expect(saveDraft).not.toHaveBeenCalled()
  })

  it('saves the answer map after 30s', async () => {
    const answers = new Map([['q1', [1]]])
    renderHook(() => useAutosave('s1', answers, true))
    await act(async () => {
      vi.advanceTimersByTime(30_000)
    })
    expect(saveDraft).toHaveBeenCalledWith('s1', { q1: [1] })
  })

  it('still saves by the max-wait cap under continuous changes (debounce never settles)', async () => {
    // Change the answers map every 10s so a pure trailing debounce would keep
    // resetting and never fire; the max-wait cap must still flush by 30s.
    const { rerender } = renderHook(
      ({ answers }) => useAutosave('s1', answers, true),
      { initialProps: { answers: new Map([['q1', [1]]]) } }
    )
    await act(async () => {
      vi.advanceTimersByTime(10_000)
    })
    rerender({ answers: new Map([['q1', [1, 2]]]) })
    await act(async () => {
      vi.advanceTimersByTime(10_000)
    })
    rerender({ answers: new Map([['q1', [1, 2, 3]]]) })
    expect(saveDraft).not.toHaveBeenCalled() // 20s in, cap not reached
    await act(async () => {
      vi.advanceTimersByTime(10_000) // 30s since mount → cap forces a save
    })
    expect(saveDraft).toHaveBeenCalledTimes(1)
  })

  it('does not re-arm the debounce when a rerender does not change content', async () => {
    // Same content, different Map reference (and different array order) on each
    // rerender. Keying on the serialized snapshot means the timer keeps running
    // toward the original 30s deadline instead of resetting every render.
    const { rerender } = renderHook(
      ({ answers }) => useAutosave('s1', answers, true),
      { initialProps: { answers: new Map([['q1', [1, 2]]]) } }
    )
    await act(async () => {
      vi.advanceTimersByTime(20_000)
    })
    rerender({ answers: new Map([['q1', [2, 1]]]) }) // equal content, new ref
    await act(async () => {
      vi.advanceTimersByTime(10_000) // 30s since mount → original timer fires
    })
    expect(saveDraft).toHaveBeenCalledTimes(1)
    expect(saveDraft).toHaveBeenCalledWith('s1', { q1: [2, 1] })
  })

  it('does not save while disabled (locked)', () => {
    const answers = new Map([['q1', [1]]])
    renderHook(() => useAutosave('s1', answers, false))
    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    expect(saveDraft).not.toHaveBeenCalled()
  })

  it('cancels a pending save on unmount', () => {
    const answers = new Map([['q1', [1]]])
    const { unmount } = renderHook(() => useAutosave('s1', answers, true))
    unmount()
    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    expect(saveDraft).not.toHaveBeenCalled()
  })
})
