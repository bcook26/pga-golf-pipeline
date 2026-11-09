import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useTournament } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { formatDate, formatMoney, formatMoneyShort, formatPoints, formatToPar } from '../lib/format'

export function TournamentPage() {
  const { id = '' } = useParams()
  const tournament = useTournament(id)
  const [filter, setFilter] = useState('')
  const [showCut, setShowCut] = useState(true)

  const data = tournament.data
  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    return (data?.results ?? []).filter(
      (r) =>
        (showCut || r.status === 'finished') &&
        (!needle || (r.player_name ?? '').toLowerCase().includes(needle)),
    )
  }, [data, filter, showCut])

  return (
    <>
      <p>
        <Link to={data ? `/tournaments?season=${data.season}` : '/tournaments'}>← Tournaments</Link>
      </p>
      <QueryStatus query={tournament} what="tournament" />
      {data && (
        <>
          <h1>{data.name}</h1>
          <dl className="bio">
            <div>
              <dt>Date</dt>
              <dd>{formatDate(data.start_date)}</dd>
            </div>
            <div>
              <dt>Course</dt>
              <dd>{[data.course_name, data.city, data.state_code].filter(Boolean).join(', ') || '–'}</dd>
            </div>
            <div>
              <dt>Purse</dt>
              <dd title={formatMoney(data.purse_usd)}>{formatMoneyShort(data.purse_usd)}</dd>
            </div>
            <div>
              <dt>Winner</dt>
              <dd>
                {data.winner_id ? (
                  <>
                    <Link to={`/players/${data.winner_id}`}>{data.winner_name ?? data.winner_id}</Link>{' '}
                    ({formatToPar(data.winning_to_par)})
                  </>
                ) : (
                  '–'
                )}
              </dd>
            </div>
            <div>
              <dt>Field</dt>
              <dd>{data.field_size} players</dd>
            </div>
          </dl>

          <form className="filters" onSubmit={(e) => e.preventDefault()}>
            <label>
              Find player
              <input
                type="search"
                value={filter}
                placeholder="e.g. scheffler"
                onChange={(e) => setFilter(e.target.value)}
              />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={showCut} onChange={(e) => setShowCut(e.target.checked)} />
              Include missed cut / withdrawn
            </label>
          </form>

          <div className="table-scroll">
            <table>
              <caption className="sr-only">Results, {data.name}</caption>
              <thead>
                <tr>
                  <th scope="col">Pos</th>
                  <th scope="col">Player</th>
                  <th scope="col" className="num">
                    To par
                  </th>
                  <th scope="col" className="num">R1</th>
                  <th scope="col" className="num">R2</th>
                  <th scope="col" className="num">R3</th>
                  <th scope="col" className="num">R4</th>
                  <th scope="col" className="num">Total</th>
                  <th scope="col" className="num">FedEx pts</th>
                  <th scope="col" className="num">Earnings</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr key={r.player_id}>
                    <td className={r.position === 1 ? 'best' : undefined}>{r.position_text ?? '–'}</td>
                    <td>
                      <Link to={`/players/${r.player_id}`}>{r.player_name ?? r.player_id}</Link>
                    </td>
                    <td className="num">{formatToPar(r.to_par)}</td>
                    {r.rounds.map((score, i) => (
                      <td key={i} className="num">
                        {score ?? '–'}
                      </td>
                    ))}
                    <td className="num">{r.total_score ?? '–'}</td>
                    <td className="num">{formatPoints(r.fedex_points)}</td>
                    <td className="num">{r.earnings_usd ? formatMoney(r.earnings_usd) : '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {visible.length === 0 && <p className="status">No players match.</p>}
        </>
      )}
    </>
  )
}
