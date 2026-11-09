import { Suspense, lazy, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useCompare, useCompareHistory, useSeasons } from '../api/hooks'
import { Marker } from '../components/Marker'
import { PlayerPicker } from '../components/PlayerPicker'
import { QueryStatus } from '../components/QueryStatus'
import { bestPlayerIds } from '../lib/compare'
import { formatRank, formatValue, titleCase } from '../lib/format'
import { addPlayer, parseSlots, removePlayer, serializeSlots, type Slotted } from '../lib/slots'

// Recharts is large; load it only when a comparison is shown.
const CompareChart = lazy(() =>
  import('../components/CompareChart').then((m) => ({ default: m.CompareChart })),
)

const DEFAULT_STAT = '02675' // SG: Total
const COLLAPSED_ROWS = 20

export function ComparePage() {
  const [params, setParams] = useSearchParams()
  const players = useMemo(() => parseSlots(params.getAll('p')), [params])
  const ids = useMemo(() => players.map((p) => p.id), [players])
  const slotOf = useMemo(() => new Map(players.map((p) => [p.id, p.slot])), [players])

  const [category, setCategory] = useState('')
  const [filter, setFilter] = useState('')
  const [commonOnly, setCommonOnly] = useState(true)
  const [showAll, setShowAll] = useState(false)

  const seasons = useSeasons()
  const season = params.get('season') ? Number(params.get('season')) : seasons.data?.[0]?.season
  const comparison = useCompare(ids, { season }, season !== undefined)

  function update(next: { players?: Slotted[]; season?: string; stat?: string | null }) {
    const sp = new URLSearchParams(params)
    if (next.players) {
      sp.delete('p')
      for (const value of serializeSlots(next.players)) sp.append('p', value)
    }
    if (next.season !== undefined) {
      if (next.season) sp.set('season', next.season)
      else sp.delete('season')
    }
    if (next.stat !== undefined) {
      if (next.stat) sp.set('stat', next.stat)
      else sp.delete('stat')
    }
    setParams(sp, { replace: true })
  }

  const stats = useMemo(() => comparison.data?.stats ?? [], [comparison.data])
  const categories = useMemo(() => [...new Set(stats.flatMap((s) => s.categories))].sort(), [stats])
  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    return stats.filter(
      (s) =>
        (!category || s.categories.includes(category)) &&
        (!needle || (s.stat_name ?? '').toLowerCase().includes(needle)) &&
        (!commonOnly || s.values.every((v) => v !== null)),
    )
  }, [stats, category, filter, commonOnly])

  const selected =
    params.get('stat') ??
    (visible.some((s) => s.stat_id === DEFAULT_STAT) ? DEFAULT_STAT : visible[0]?.stat_id)
  const history = useCompareHistory(ids, selected)

  const compared = comparison.data?.players ?? []
  const series = (history.data?.series ?? []).map((s) => ({
    id: s.player_id,
    name: s.display_name,
    slot: slotOf.get(s.player_id) ?? 0,
    points: s.points,
  }))

  return (
    <>
      <h1>Compare players</h1>
      <p className="muted">Pick 2–4 players to see their stats side by side and how they trend over seasons.</p>

      <PlayerPicker
        selected={players}
        onAdd={(id) => update({ players: addPlayer(players, id) })}
        onRemove={(id) => update({ players: removePlayer(players, id), stat: undefined })}
      />

      {players.length < 2 ? (
        <p className="status">{players.length === 0 ? 'Add at least two players to compare.' : 'Add one more player to start comparing.'}</p>
      ) : (
        <>
          <QueryStatus query={comparison} what="comparison" />
          {comparison.data && (
            <>
              {selected && series.length > 0 && history.data && (
                <Suspense fallback={<p className="status">Loading chart…</p>}>
                  <CompareChart title={history.data.stat_name ?? selected} series={series} />
                </Suspense>
              )}
              {selected && <QueryStatus query={history} what="trend" />}

              <h2>Head to head · {comparison.data.season}</h2>
              <form className="filters" onSubmit={(e) => e.preventDefault()}>
                <label>
                  Season
                  <select value={season ?? ''} onChange={(e) => update({ season: e.target.value })}>
                    {seasons.data?.map((s) => (
                      <option key={s.season} value={s.season}>
                        {s.season}
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
                  <input type="search" value={filter} placeholder="e.g. putting" onChange={(e) => setFilter(e.target.value)} />
                </label>
                <label className="checkbox">
                  <input type="checkbox" checked={commonOnly} onChange={(e) => setCommonOnly(e.target.checked)} />
                  Only stats all players have
                </label>
              </form>

              <p className="muted legend-note">
                The best rank in each row is highlighted. #1 is best whichever direction the stat runs.
              </p>
              <div className="table-scroll">
                <table>
                  <caption className="sr-only">Head-to-head statistics, {comparison.data.season}</caption>
                  <thead>
                    <tr>
                      <th scope="col">Stat (select to chart)</th>
                      {compared.map((p) => (
                        <th key={p.player_id} scope="col" className="num">
                          <span className="th-player">
                            <Marker slot={slotOf.get(p.player_id) ?? 0} size={10} />
                            <Link to={`/players/${p.player_id}`}>{p.display_name}</Link>
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(showAll ? visible : visible.slice(0, COLLAPSED_ROWS)).map((stat) => {
                      const best = bestPlayerIds(stat)
                      return (
                        <tr key={stat.stat_id} className={stat.stat_id === selected ? 'selected' : undefined}>
                          <td>
                            <button
                              type="button"
                              className="link"
                              aria-pressed={stat.stat_id === selected}
                              onClick={() => update({ stat: stat.stat_id })}
                            >
                              {stat.stat_name ?? stat.stat_id}
                            </button>
                          </td>
                          {compared.map((p, i) => {
                            const v = stat.values[i]
                            const isBest = best.has(p.player_id)
                            return (
                              <td key={p.player_id} className={`num${isBest ? ' best' : ''}`}>
                                {formatValue(v?.stat_value)} <span className="muted">{formatRank(v?.rank)}</span>
                                {isBest && <span className="sr-only"> (best rank)</span>}
                              </td>
                            )
                          })}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {visible.length > COLLAPSED_ROWS && (
                <p>
                  <button type="button" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? 'Show fewer stats' : `Show all ${visible.length} stats`}
                  </button>
                </p>
              )}
              {visible.length === 0 && <p className="status">No stats match these filters.</p>}
            </>
          )}
        </>
      )}
    </>
  )
}
