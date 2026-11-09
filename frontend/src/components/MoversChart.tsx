import type { Movers } from '../api/client'
import { formatValue } from '../lib/format'

/**
 * Diverging bars of rank change between two seasons: blue = moved up the
 * rankings, red = moved down, around a neutral centre line. Uses rank, so
 * "up" is right even for lower-is-better stats. Each row states its numbers.
 */
export function MoversChart({ movers }: { movers: Movers }) {
  const rows = [...movers.improvers, ...[...movers.decliners].reverse()]
  const largest = Math.max(1, ...rows.map((m) => Math.abs(m.rank_change)))
  return (
    <ol className="movers" aria-label={`Rank change in ${movers.stat_name}, ${movers.compare_to} to ${movers.season}`}>
      {rows.map((m) => {
        const up = m.rank_change > 0
        const width = `${(Math.abs(m.rank_change) / largest) * 50}%`
        return (
          <li key={m.player_id} className="mover-row">
            <span className="mover-name">{m.player_name ?? m.player_id}</span>
            <span className="mover-track" aria-hidden="true">
              <span className={`mover-bar ${up ? 'up' : 'down'}`} style={up ? { left: '50%', width } : { right: '50%', width }} />
            </span>
            <span className="mover-text">
              <strong>
                {up ? '▲' : '▼'} {Math.abs(m.rank_change)}
              </strong>{' '}
              places · #{m.rank_from} → #{m.rank_to}
              <span className="muted">
                {' '}
                · {formatValue(m.value_from)} → {formatValue(m.value_to)}
              </span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}
