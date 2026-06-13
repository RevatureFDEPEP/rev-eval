import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>(
    '@/lib/api/client'
  )
  return {
    ...actual,
    api: {
      post: vi.fn(),
      patch: vi.fn(),
    },
  }
})

import { api } from '@/lib/api/client'
import { saveDraft, submitAnswer } from '@/lib/api/sessions'

const transient = () => new ApiError(503, 'Service Unavailable', '')

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(api.post).mockReset()
  vi.mocked(api.patch).mockReset()
})
afterEach(() => {
  vi.useRealTimers()
})

describe('saveDraft', () => {
  it('does not retry on a transient failure (single attempt)', async () => {
    vi.mocked(api.patch).mockRejectedValue(transient())
    await expect(saveDraft('s1', { q1: [1] })).rejects.toBeInstanceOf(ApiError)
    expect(api.patch).toHaveBeenCalledTimes(1)
  })

  it('sends the answers map to the draft endpoint', async () => {
    vi.mocked(api.patch).mockResolvedValue({} as never)
    await saveDraft('s1', { q1: [1, 2] })
    expect(api.patch).toHaveBeenCalledWith('/v1/api/sessions/s1/draft', {
      answers: { q1: [1, 2] },
    })
  })
})

describe('submitAnswer', () => {
  it('retries a transient failure, reusing the same Idempotency-Key', async () => {
    vi.mocked(api.post)
      .mockRejectedValueOnce(transient())
      .mockResolvedValueOnce({} as never)
    const promise = submitAnswer('s1', [1], 'q1', 'key-123')
    await vi.runAllTimersAsync()
    await promise
    expect(api.post).toHaveBeenCalledTimes(2)
    for (const call of vi.mocked(api.post).mock.calls) {
      expect(call[2]).toEqual({ headers: { 'Idempotency-Key': 'key-123' } })
    }
  })
})
