import type { UseQueryResult } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'

/** After this long, reassure the user that the request is still running. */
const SLOW_AFTER_MS = 6000

function Loading({ what }: { what: string }) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => clearTimeout(timer)
  }, [])
  return (
    <p className="status" role="status">
      Loading {what}…
      {slow && (
        <>
          <br />
          <span className="muted">
            Still working, this is taking longer than usual.
          </span>
        </>
      )}
    </p>
  )
}

/** Renders loading / error states for a query; renders nothing when data is ready. */
export function QueryStatus({ query, what }: { query: UseQueryResult; what: string }) {
  if (query.isPending) return <Loading what={what} />
  if (query.isError) {
    const error = query.error
    const notFound = error instanceof ApiError && error.status === 404
    // Rate limited: the message says how long to wait, and retrying now would only extend it.
    const limited = error instanceof ApiError && error.status === 429
    return (
      <div className="status status-error" role="alert">
        <p>{notFound ? `Not found: ${error.message}` : `Could not load ${what}. ${error.message}`}</p>
        {!notFound && !limited && (
          <button type="button" onClick={() => void query.refetch()}>
            Retry
          </button>
        )}
      </div>
    )
  }
  return null
}
