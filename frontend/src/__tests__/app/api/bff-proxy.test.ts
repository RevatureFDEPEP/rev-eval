import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { NextRequest } from 'next/server'

vi.mock('@/lib/session', () => ({
  getSession: vi.fn(),
}))

import { getSession } from '@/lib/session'
import { PATCH } from '@/app/api/v1/[...path]/route'

const SESSION = { userId: 1, email: 'p@x.com', role: 'PARTICIPANT', token: 'jwt' }

function req(body = '{"answers":{}}', headers: Record<string, string> = {}) {
  return {
    method: 'PATCH',
    nextUrl: new URL('http://localhost/api/v1/api/sessions/s1/draft'),
    headers: new Headers(headers),
    text: async () => body,
  } as unknown as NextRequest
}

const ctx = { params: { path: ['api', 'sessions', 's1', 'draft'] } }

beforeEach(() => {
  vi.mocked(getSession).mockResolvedValue(SESSION)
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('BFF proxy', () => {
  it('returns 502 (retryable) when the gateway connection fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('fetch failed'))
    )
    const res = await PATCH(req(), ctx)
    expect(res.status).toBe(502)
    await expect(res.json()).resolves.toEqual({
      error: 'Upstream service unavailable',
    })
  })

  it('forwards the downstream status and body on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ saved_at: 't' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    )
    const res = await PATCH(req(), ctx)
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({ saved_at: 't' })
  })

  it('does not send a duplicate Content-Type when the client set one', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('null', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await PATCH(req('{}', { 'content-type': 'application/json' }), ctx)
    const sentHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(sentHeaders['Content-Type']).toBe('application/json')
    // No comma-joined collision.
    expect(sentHeaders['Content-Type']).not.toContain(',')
  })

  it('rejects an unauthenticated request with 401 before reaching the gateway', async () => {
    vi.mocked(getSession).mockResolvedValue(null)
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const res = await PATCH(req(), ctx)
    expect(res.status).toBe(401)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
