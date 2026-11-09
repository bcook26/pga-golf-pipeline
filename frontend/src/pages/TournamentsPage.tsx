import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useSeasons, useTournaments } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { formatDate, formatMoney, formatMoneyShort, formatToPar } from '../lib/format'
import { useDebounced } from '../lib/useDebounced'

const STATUS_LABEL: Record<string, string> = {
  in_progress: 'In progress',
  upcoming: 'Upcoming',
}

export function TournamentsPage() {
  const [params, setParams] = useSearchParams()
  const seasons = useSeasons()
  const season = params.get('season') ? Number(params.get('season')) : seasons.data?.[0]?.season
  const category = params.get('category') ?? ''
  const [search, setSearch] = useState(params.get('q') ?? '')
  const q = useDebounced(search, 250)

  const tournaments = useTournaments({
    season,
    search: q || undefined,
    category: category || undefined,
  })

  function setParam(key: string, value: string) {
    const sp = new URLSearchParams(params)
    if (value) sp.set(key, value)
    else sp.delete(key)
    setParams(sp, { replace: true })
  }

  return (
    <>
      <h1>Tournaments</h1>
      <p className="muted">Winners and results for individual stroke-play events.</p>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Season
          <select value={season ?? ''} onChange={(e) => setParam('season', e.target.value)}>
            {seasons.data?.map((s) => (
              <option key={s.season} value={s.season}>
                {s.season}
              </option>
            ))}
          </select>
        </label>
        <label>
          Type
          <select value={category} onChange={(e) => setParam('category', e.target.value)}>
            <option value="">All</option>
            <option value="SIGNATURE">Signature events</option>
            <option value="PLAYOFF">FedExCup Playoffs</option>
          </select>
        </label>
        <label>
          Search
          <input
            type="search"
            value={search}
            placeholder="e.g. open"
            onChange={(e) => {
              setSearch(e.target.value)
              setParam('q', e.target.value)
            }}
          />
        </label>
      </form>

      <QueryStatus query={tournaments} what="tournaments" />
      {tournaments.data && tournaments.data.length === 0 && (
        <p className="status">No tournaments match these filters.</p>
      )}
      {tournaments.data && tournaments.data.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Tournaments, {season}</caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Tournament</th>
                <th scope="col">Course</th>
                <th scope="col">Winner</th>
                <th scope="col" className="num">
                  Score
                </th>
                <th scope="col" className="num">
                  Purse
                </th>
              </tr>
            </thead>
            <tbody>
              {tournaments.data.map((t) => (
                <tr key={t.tournament_id}>
                  <td className="nowrap">{formatDate(t.start_date)}</td>
                  <td>
                    {t.field_size > 0 ? (
                      <Link to={`/tournaments/${t.tournament_id}`}>{t.name}</Link>
                    ) : (
                      t.name
                    )}
                    {t.category && (
                      <span className="tag">{t.category === 'PLAYOFF' ? 'Playoffs' : 'Signature'}</span>
                    )}
                  </td>
                  <td>{[t.course_name, t.city].filter(Boolean).join(' · ') || '–'}</td>
                  <td>
                    {t.winner_id ? (
                      <Link to={`/players/${t.winner_id}`}>{t.winner_name ?? t.winner_id}</Link>
                    ) : (
                      <span className="muted">{STATUS_LABEL[t.status ?? ''] ?? '–'}</span>
                    )}
                  </td>
                  <td className="num">{t.winner_id ? formatToPar(t.winning_to_par) : '–'}</td>
                  <td className="num" title={formatMoney(t.purse_usd)}>
                    {formatMoneyShort(t.purse_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
