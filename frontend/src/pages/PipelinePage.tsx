import { usePipelineStatus } from '../api/hooks'
import { QueryStatus } from '../components/QueryStatus'
import { StatusBadge } from '../components/StatusBadge'
import { formatAge, formatDuration } from '../lib/stats'

const HEADLINE: Record<string, string> = {
  ok: 'Pipeline healthy',
  warn: 'Pipeline needs attention',
  fail: 'Pipeline failing',
}

function when(iso: string | null | undefined) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

export function PipelinePage() {
  const status = usePipelineStatus()
  const data = status.data

  return (
    <>
      <h1>Pipeline health</h1>
      <p className="muted">Freshness of the warehouse, data-quality checks and recent ETL runs. Refreshes every 30 seconds.</p>
      <QueryStatus query={status} what="pipeline status" />
      {data && (
        <>
          <section className={`banner banner-${data.overall}`} aria-label="Overall status">
            <StatusBadge status={data.overall} />
            <div>
              <strong>{HEADLINE[data.overall] ?? data.overall}</strong>
              {data.reasons.length > 0 ? (
                <ul>
                  {data.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">All seasons are fresh and every quality check passed.</p>
              )}
            </div>
          </section>

          <h2>Seasons</h2>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">Rows and freshness per season</caption>
              <thead>
                <tr>
                  <th scope="col">Season</th>
                  <th scope="col" className="num">Rows</th>
                  <th scope="col" className="num">Players</th>
                  <th scope="col" className="num">Stats</th>
                  <th scope="col">Last success</th>
                  <th scope="col">Last run</th>
                </tr>
              </thead>
              <tbody>
                {data.seasons.map((s) => (
                  <tr key={s.season}>
                    <th scope="row">{s.season}</th>
                    <td className="num">{s.rows.toLocaleString()}</td>
                    <td className="num">{s.players.toLocaleString()}</td>
                    <td className="num">{s.stats.toLocaleString()}</td>
                    <td>
                      {when(s.last_success_at)} <span className="muted">({formatAge(s.age_seconds)})</span>
                    </td>
                    <td>{s.last_run_status ? <StatusBadge status={s.last_run_status} /> : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Data-quality checks</h2>
          {data.quality.length === 0 ? (
            <p className="status">No checks recorded yet. They run on every stats load.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <caption className="sr-only">Latest data-quality result per season and check</caption>
                <thead>
                  <tr>
                    <th scope="col">Status</th>
                    <th scope="col">Season</th>
                    <th scope="col">Check</th>
                    <th scope="col">Detail</th>
                    <th scope="col">Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {data.quality.map((q) => (
                    <tr key={`${q.season}-${q.check_name}`}>
                      <td>
                        <StatusBadge status={q.status} />
                      </td>
                      <td>{q.season ?? '—'}</td>
                      <td>{q.check_name}</td>
                      <td>{q.detail ?? ''}</td>
                      <td>{when(q.checked_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2>Recent runs</h2>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">Recent ETL runs, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col">Pipeline</th>
                  <th scope="col">Mode</th>
                  <th scope="col">Season</th>
                  <th scope="col" className="num">Rows</th>
                  <th scope="col" className="num">Duration</th>
                  <th scope="col">Started</th>
                </tr>
              </thead>
              <tbody>
                {data.runs.map((r) => (
                  <tr key={r.run_id}>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>{r.pipeline}</td>
                    <td>{r.mode}</td>
                    <td>{r.season ?? '—'}</td>
                    <td className="num">{r.rows_loaded?.toLocaleString() ?? '—'}</td>
                    <td className="num">{formatDuration(r.duration_seconds)}</td>
                    <td>{when(r.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  )
}
