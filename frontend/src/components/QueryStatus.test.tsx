import { render, screen } from '@testing-library/react'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import { QueryStatus } from './QueryStatus'

const q = (state: Record<string, unknown>) => state as never

describe('QueryStatus', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('explains a slow first load after a few seconds', () => {
    render(<QueryStatus query={q({ isPending: true })} what="players" />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading players…')
    expect(screen.queryByText(/free server sleeps/i)).not.toBeInTheDocument()
    act(() => {
      vi.advanceTimersByTime(6500)
    })
    expect(screen.getByText(/free server sleeps/i)).toBeInTheDocument()
  })

  it('shows the wait time for a rate limit and offers no retry', () => {
    const error = new ApiError(429, 'Too many requests from your connection. Try again in 42 seconds.')
    render(<QueryStatus query={q({ isPending: false, isError: true, error })} what="players" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Try again in 42 seconds')
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  it('still offers retry for server errors', () => {
    const error = new ApiError(500, 'boom')
    render(<QueryStatus query={q({ isPending: false, isError: true, error, refetch: vi.fn() })} what="players" />)
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
