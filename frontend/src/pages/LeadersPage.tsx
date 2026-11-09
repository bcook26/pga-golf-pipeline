import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import type { StatDefinition } from '../api/client'
import { useLeaders, useSeasons, useStatCatalogue } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { formatRank, formatValue, titleCase } from '../lib/format'

const DEFAULT_STAT = '02675'
const LIMITS = [10, 25, 50, 100]

export function LeadersPage() {
  const [params, setParams] = useSearchParams()
  const statId = params.get('stat') ?? DEFAULT_STAT
  const season = params.get('season') ? Number(params.get('season')) : undefined
  const limit = Number(params.get('limit') ?? 25)

  const catalogue = useStatCatalogue()
  const seasons = useSeasons()
  const leaders = useLeaders(statId, { season, limit })

  const grouped = useMemo(() => {
    const groups = new Map<string, StatDefinition[]>()
    for (const stat of catalogue.data ?? []) {
      const key = stat.categories[0] ?? 'OTHER'
      groups.set(key, [...(groups.get(key) ?? []), stat])
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [catalogue.data])

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value === '') next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }

  return (
    <>
      <h1>Leaderboards</h1>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Stat
          <select value={statId} onChange={(e) => setParam('stat', e.target.value)}>
            {grouped.map(([group, stats]) => (
              <optgroup key={group} label={titleCase(group)}>
                {stats.map((s) => (
                  <option key={s.stat_id} value={s.stat_id}>
                    {s.stat_name}
                  </option>
                ))}
              </optgroup>
            ))}
            {!catalogue.data && <option value={statId}>{statId}</option>}
          </select>
        </label>
        <label>
          Season
          <select value={season ?? ''} onChange={(e) => setParam('season', e.target.value)}>
            <option value="">Latest</option>
            {seasons.data?.map((s) => (
              <option key={s.season} value={s.season}>
                {s.season}
              </option>
            ))}
          </select>
        </label>
        <label>
          Show
          <select value={limit} onChange={(e) => setParam('limit', e.target.value)}>
            {LIMITS.map((n) => (
              <option key={n} value={n}>
                Top {n}
              </option>
            ))}
          </select>
        </label>
      </form>

      <QueryStatus query={leaders} what="leaderboard" />
      {leaders.data && (
        <>
          <h2>
            {leaders.data.stat_name} · {leaders.data.season}
          </h2>
          <table>
            <caption className="sr-only">
              {leaders.data.stat_name} leaderboard, {leaders.data.season}
            </caption>
            <thead>
              <tr>
                <th scope="col" className="num">
                  Rank
                </th>
                <th scope="col">Player</th>
                <th scope="col" className="num">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {leaders.data.rows.map((r) => (
                <tr key={r.player_id}>
                  <td className="num">{formatRank(r.rank)}</td>
                  <td>
                    <Link to={`/players/${r.player_id}`}>{r.player_name ?? r.player_id}</Link>
                  </td>
                  <td className="num">{formatValue(r.stat_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  )
}
