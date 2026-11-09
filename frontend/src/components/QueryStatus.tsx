import type { UseQueryResult } from '@tanstack/react-query'

import { ApiError } from '../api/client'

/** Renders loading / error states for a query; renders nothing when data is ready. */
export function QueryStatus({ query, what }: { query: UseQueryResult; what: string }) {
  if (query.isPending) {
    return (
      <p className="status" role="status">
        Loading {what}…
      </p>
    )
  }
  if (query.isError) {
    const error = query.error
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <div className="status status-error" role="alert">
        <p>{notFound ? `Not found: ${error.message}` : `Could not load ${what}. ${error.message}`}</p>
        {!notFound && (
          <button type="button" onClick={() => void query.refetch()}>
            Retry
          </button>
        )}
      </div>
    )
  }
  return null
}
