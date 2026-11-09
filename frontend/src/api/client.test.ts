import { describe, expect, it, vi } from 'vitest'

import { ApiError, api, buildUrl } from './client'

describe('buildUrl', () => {
  it('skips empty params and encodes values', () => {
    const url = buildUrl('/api/v1/players', { search: 'a b&c', season: 2024, active: undefined, x: '' })
    expect(url).toContain('/api/v1/players?')
    expect(url).toContain('search=a+b%26c')
    expect(url).toContain('season=2024')
    expect(url).not.toContain('active')
    expect(url).not.toContain('x=')
  })
})

describe('api', () => {
  it('throws ApiError with the server detail on 404', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Player X not found' }), { status: 404 })))
    await expect(api.player('X')).rejects.toMatchObject({ status: 404, message: 'Player X not found' })
  })

  it('maps network failures to a friendly ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    const error = await api.seasons().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toMatch(/Cannot reach the API/)
  })

  it('url-encodes path ids', async () => {
    const fetchMock = vi.fn(async (..._args: unknown[]) => new Response('[]', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.playerStats('a/b', { season: 2024 })
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/players/a%2Fb/stats?season=2024')
  })
})
