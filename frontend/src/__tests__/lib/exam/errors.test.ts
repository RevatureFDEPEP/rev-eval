import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'
import { classifyError, errorStatus, fetchWithRetry } from '@/lib/exam/errors'

describe('classifyError', () => {
  it('treats a network failure (no status) as transient', () => {
    expect(classifyError(undefined)).toBe('transient')
  })

  it('treats 502/503/504 as transient', () => {
    expect(classifyError(502)).toBe('transient')
    expect(classifyError(503)).toBe('transient')
    expect(classifyError(504)).toBe('transient')
  })

  it('treats 409/410/422 as semantic', () => {
    expect(classifyError(409)).toBe('semantic')
    expect(classifyError(410)).toBe('semantic')
    expect(classifyError(422)).toBe('semantic')
  })

  it('defaults other statuses to semantic so they do not retry-storm', () => {
    expect(classifyError(400)).toBe('semantic')
    expect(classifyError(500)).toBe('semantic')
  })
})

describe('errorStatus', () => {
  it('reads the status off an ApiError', () => {
    expect(errorStatus(new ApiError(409, 'Conflict', null))).toBe(409)
  })

  it('returns undefined for a plain (network) Error', () => {
    expect(errorStatus(new Error('network down'))).toBeUndefined()
  })
})

describe('fetchWithRetry', () => {
  it('retries a transient failure then resolves', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, 'Unavailable', null))
      .mockResolvedValueOnce('ok')
    await expect(fetchWithRetry(fn, { baseMs: 0 })).resolves.toBe('ok')
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('does not retry a semantic failure', async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(422, 'Unprocessable', null))
    await expect(fetchWithRetry(fn, { baseMs: 0 })).rejects.toBeInstanceOf(ApiError)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('gives up after maxRetries on a persistent transient failure', async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(503, 'Unavailable', null))
    await expect(
      fetchWithRetry(fn, { baseMs: 0, maxRetries: 2 })
    ).rejects.toBeInstanceOf(ApiError)
    expect(fn).toHaveBeenCalledTimes(3) // initial + 2 retries
  })
})
