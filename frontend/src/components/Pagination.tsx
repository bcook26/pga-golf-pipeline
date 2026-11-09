export function Pagination({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number
  limit: number
  offset: number
  onChange: (offset: number) => void
}) {
  if (total === 0) return null
  const from = offset + 1
  const to = Math.min(offset + limit, total)
  return (
    <nav className="pagination" aria-label="Pagination">
      <span>
        {from}–{to} of {total.toLocaleString()}
      </span>
      <button type="button" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </button>
      <button type="button" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
        Next
      </button>
    </nav>
  )
}
