import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

/** Mock fetch with a route table: [substring of URL, JSON body or [status, body]]. */
export function mockApi(routes: Array<[string, unknown]>) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      calls.push(url)
      const hit = [...routes].reverse().find(([needle]) => url.includes(needle))
      if (!hit) return new Response(JSON.stringify({ detail: 'no route' }), { status: 404 })
      const [, body] = hit
      const [status, payload] = Array.isArray(body) && typeof body[0] === 'number' ? body : [200, body]
      return new Response(JSON.stringify(payload), {
        status: status as number,
        headers: { 'content-type': 'application/json' },
      })
    }),
  )
  return calls
}

export function renderAt(ui: ReactElement, path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}
