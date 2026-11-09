import type { PercentileStat } from '../api/client'
import { formatValue } from '../lib/format'
import { ordinal } from '../lib/stats'

/**
 * Lollipop of each stat's percentile within the field (100 = best, #1).
 * The 50th-percentile guide is the field median. Every row also states its
 * numbers in text, so nothing depends on seeing the chart.
 */
export function PercentileProfile({ stats }: { stats: PercentileStat[] }) {
  return (
    <div className="pct">
      <div className="pct-axis" aria-hidden="true">
        <span>Worst in field</span>
        <span>Median</span>
        <span>Best</span>
      </div>
      <ul aria-label="Percentile rank of each stat within the field">
        {stats.map((s) => (
          <li key={s.stat_id} className="pct-row">
            <span className="pct-name">{s.stat_name ?? s.stat_id}</span>
            <span className="pct-track" aria-hidden="true">
              <span className="pct-stem" style={{ width: `${s.percentile}%` }} />
              <span className="pct-dot" style={{ left: `${s.percentile}%` }} />
            </span>
            <span className="pct-text">
              <strong>{ordinal(s.percentile)}</strong> percentile · #{s.rank} of {s.field_size}
              <span className="muted"> · {formatValue(s.stat_value)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
