import { Link, useSearchParams } from 'react-router-dom'

import { useLeaders, useSeasons } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { StatSelect } from '../components/StatSelect'
import { formatRank, formatValue } from '../lib/format'

const DEFAULT_STAT = '02675'
const LIMITS = [10, 25, 50, 100]

export function LeadersPage() {
  const [params, setParams] = useSearchParams()
  const statId = params.get('stat') ?? DEFAULT_STAT
  const season = params.get('season') ? Number(params.get('season')) : undefined
  const limit = Number(params.get('limit') ?? 25)

  const seasons = useSeasons()
  const leaders = useLeaders(statId, { season, limit })

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
        <StatSelect label="Stat" value={statId} onChange={(id) => setParam('stat', id)} />
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
