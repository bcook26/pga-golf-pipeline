import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { usePlayers, useSeasons } from '../api/hooks'
import { Pagination } from '../components/Pagination'
import { QueryStatus } from '../components/QueryStatus'
import { useDebounced } from '../lib/useDebounced'

const PAGE_SIZE = 25

export function PlayersPage() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const season = params.get('season') ? Number(params.get('season')) : undefined
  const activeOnly = params.get('active') === '1'
  const offset = Number(params.get('offset') ?? 0)

  // Keep typing responsive; only the debounced value hits the API / URL.
  const [text, setText] = useState(q)
  const debounced = useDebounced(text)
  useEffect(() => {
    if (debounced !== q) update({ q: debounced, offset: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced])

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === '') next.delete(key)
      else next.set(key, value)
    }
    setParams(next, { replace: true })
  }

  const seasons = useSeasons()
  const players = usePlayers({
    search: q || undefined,
    season,
    has_stats: true,
    active: activeOnly ? true : undefined,
    limit: PAGE_SIZE,
    offset,
  })

  return (
    <>
      <h1>Players</h1>
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <label>
          Search by name
          <input
            type="search"
            value={text}
            placeholder="e.g. Scheffler"
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <label>
          Season
          <select value={season ?? ''} onChange={(e) => update({ season: e.target.value, offset: null })}>
            <option value="">Any</option>
            {seasons.data?.map((s) => (
              <option key={s.season} value={s.season}>
                {s.season}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => update({ active: e.target.checked ? '1' : null, offset: null })}
          />
          Active players only
        </label>
      </form>

      <QueryStatus query={players} what="players" />
      {players.data && (
        <>
          {players.data.items.length === 0 ? (
            <p className="status">No players match these filters.</p>
          ) : (
            <table>
              <caption className="sr-only">Players</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Country</th>
                  <th scope="col">Primary tour</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {players.data.items.map((p) => (
                  <tr key={p.player_id}>
                    <td>
                      <Link to={`/players/${p.player_id}`}>{p.display_name}</Link>
                    </td>
                    <td>{p.country ?? '–'}</td>
                    <td>{p.primary_tour ?? '–'}</td>
                    <td>{p.is_active === null ? '–' : p.is_active ? 'Active' : 'Inactive'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Pagination
            total={players.data.total}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={(o) => update({ offset: o === 0 ? null : String(o) })}
          />
        </>
      )}
    </>
  )
}
