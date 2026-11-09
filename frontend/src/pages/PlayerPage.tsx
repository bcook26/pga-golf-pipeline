import { Suspense, lazy, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import type { PlayerStat } from '../api/client'
import { usePlayer, usePlayerStats, useStatHistory } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { formatRank, formatValue, titleCase } from '../lib/format'

// Recharts is large; load it only on the player page.
const TrendChart = lazy(() =>
  import('../components/TrendChart').then((m) => ({ default: m.TrendChart })),
)

const DEFAULT_STAT = '02675' // SG: Total

function BioList({ bio }: { bio: Record<string, unknown> | null }) {
  const entries = Object.entries(bio ?? {}).filter(([k, v]) => k !== 'id' && v !== null && v !== '')
  if (entries.length === 0) return null
  return (
    <dl className="bio">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt>{titleCase(key.replace(/([A-Z])/g, '_$1'))}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

export function PlayerPage() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const [category, setCategory] = useState<string>('')
  const [filter, setFilter] = useState('')

  const player = usePlayer(id)
  const seasons = player.data?.seasons ?? []
  const season = params.get('season') ? Number(params.get('season')) : seasons[0]
  const stats = usePlayerStats(id, { season }, season !== undefined)

  const rows = useMemo(
    () => [...(stats.data ?? [])].sort((a, b) => (a.stat_name ?? '').localeCompare(b.stat_name ?? '')),
    [stats.data],
  )
  const categories = useMemo(() => [...new Set(rows.flatMap((r) => r.categories))].sort(), [rows])
  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    return rows.filter(
      (r: PlayerStat) =>
        (!category || r.categories.includes(category)) &&
        (!needle || (r.stat_name ?? '').toLowerCase().includes(needle)),
    )
  }, [rows, category, filter])

  const selected =
    params.get('stat') ??
    (rows.some((r) => r.stat_id === DEFAULT_STAT) ? DEFAULT_STAT : rows[0]?.stat_id)
  const history = useStatHistory(id, selected)

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value === null) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }

  if (player.isPending || player.isError) {
    return <QueryStatus query={player} what="player" />
  }

  return (
    <>
      <p className="crumbs">
        <Link to="/">← All players</Link>
        <Link to={`/compare?p=0:${encodeURIComponent(id)}`}>Compare with other players →</Link>
      </p>
      <h1>{player.data.display_name}</h1>
      <p className="muted">
        {[player.data.country, player.data.primary_tour, player.data.is_active ? 'Active' : null]
          .filter(Boolean)
          .join(' · ')}
      </p>
      <BioList bio={player.data.bio} />

      {seasons.length === 0 ? (
        <p className="status">No statistics have been loaded for this player.</p>
      ) : (
        <>
          {selected && history.data && (
            <Suspense fallback={<p className="status">Loading chart…</p>}>
              <TrendChart title={history.data.stat_name ?? selected} points={history.data.points} />
            </Suspense>
          )}
          {selected && <QueryStatus query={history} what="trend" />}

          <h2>Statistics</h2>
          <form className="filters" onSubmit={(e) => e.preventDefault()}>
            <label>
              Season
              <select value={season} onChange={(e) => setParam('season', e.target.value)}>
                {seasons.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">All</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {titleCase(c)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Filter stats
              <input
                type="search"
                value={filter}
                placeholder="e.g. putting"
                onChange={(e) => setFilter(e.target.value)}
              />
            </label>
          </form>

          <QueryStatus query={stats} what="statistics" />
          {stats.data && (
            <table>
              <caption className="sr-only">
                {player.data.display_name} statistics, {season}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Stat (select to chart)</th>
                  <th scope="col" className="num">
                    Value
                  </th>
                  <th scope="col" className="num">
                    Rank
                  </th>
                  <th scope="col">Category</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr key={r.stat_id} className={r.stat_id === selected ? 'selected' : undefined}>
                    <td>
                      <button
                        type="button"
                        className="link"
                        aria-pressed={r.stat_id === selected}
                        onClick={() => setParam('stat', r.stat_id)}
                      >
                        {r.stat_name ?? r.stat_id}
                      </button>
                    </td>
                    <td className="num">{formatValue(r.stat_value)}</td>
                    <td className="num">{formatRank(r.rank)}</td>
                    <td>{r.categories.map(titleCase).join(', ') || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {stats.data && visible.length === 0 && <p className="status">No stats match these filters.</p>}
        </>
      )}
    </>
  )
}
