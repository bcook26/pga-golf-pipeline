import { type Key, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatRank, formatValue } from '../lib/format'
import { seriesColor, shapePath } from '../lib/series'
import { Marker } from './Marker'

export interface CompareSeries {
  id: string
  name: string
  slot: number
  points: Array<{ season: number; stat_value: number | null; rank: number | null }>
}

type Row = { season: number } & Record<string, number | null>

function SeriesDot({ cx, cy, slot }: { cx?: number; cy?: number; slot: number }) {
  if (cx === undefined || cy === undefined) return <g />
  // 2px surface ring keeps overlapping markers distinguishable
  return (
    <path
      transform={`translate(${cx},${cy})`}
      d={shapePath(slot, 4.5)}
      fill={seriesColor(slot)}
      stroke="var(--surface-1)"
      strokeWidth={2}
    />
  )
}

function CompareTooltip({
  active,
  label,
  series,
}: {
  active?: boolean
  label?: number | string
  series: CompareSeries[]
}) {
  if (!active || label === undefined) return null
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {series.map((s) => {
        const p = s.points.find((pt) => pt.season === Number(label))
        return (
          <div key={s.id} className="tip-row">
            <Marker slot={s.slot} size={10} />
            <span>{s.name}</span>
            <span className="num">
              {formatValue(p?.stat_value)} ({formatRank(p?.rank)})
            </span>
          </div>
        )
      })}
    </div>
  )
}

/**
 * Multi-series trend of one stat. Single y-axis (value); rank is in the
 * tooltip and table. Identity = colour + marker shape + a legend that also
 * carries each player's latest value (the "direct label"), so it works without
 * colour or hover. A table view is one click away.
 */
export function CompareChart({ title, series }: { title: string; series: CompareSeries[] }) {
  const [view, setView] = useState<'chart' | 'table'>('chart')

  const { rows, seasons } = useMemo(() => {
    const seasonSet = new Set(series.flatMap((s) => s.points.map((p) => p.season)))
    const sorted = [...seasonSet].sort((a, b) => a - b)
    const data: Row[] = sorted.map((season) => {
      const row: Row = { season }
      for (const s of series) row[s.id] = s.points.find((p) => p.season === season)?.stat_value ?? null
      return row
    })
    return { rows: data, seasons: sorted }
  }, [series])

  const summary = series
    .map(
      (s) =>
        `${s.name}: ` +
        s.points.map((p) => `${p.season} ${formatValue(p.stat_value)} (rank ${formatRank(p.rank)})`).join(', '),
    )
    .join('. ')

  return (
    <section className="card" aria-label={`${title} by season, compared`}>
      <header className="card-header">
        <h3>{title} by season</h3>
        <div className="segmented" role="group" aria-label="Chart view">
          <button type="button" aria-pressed={view === 'chart'} onClick={() => setView('chart')}>
            Chart
          </button>
          <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}>
            Table
          </button>
        </div>
      </header>

      <ul className="legend" aria-label="Legend">
        {series.map((s) => {
          const latest = [...s.points].reverse().find((p) => p.stat_value !== null)
          return (
            <li key={s.id}>
              <Marker slot={s.slot} />
              <span>{s.name}</span>
              {latest && (
                <span className="muted">
                  {formatValue(latest.stat_value)} in {latest.season}
                </span>
              )}
            </li>
          )
        })}
      </ul>

      {view === 'chart' ? (
        <div className="chart" role="img" aria-label={`${title} by season. ${summary}`}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={rows} margin={{ top: 12, right: 24, bottom: 4, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--grid)" />
              <XAxis
                dataKey="season"
                tickLine={false}
                padding={{ left: 16, right: 16 }}
                axisLine={{ stroke: 'var(--grid-strong)' }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={48}
                domain={['auto', 'auto']}
                tickFormatter={(v: number) => formatValue(v)}
              />
              <Tooltip
                content={<CompareTooltip series={series} />}
                cursor={{ stroke: 'var(--grid-strong)', strokeWidth: 1 }}
                offset={24}
              />
              {series.map((s) => (
                <Line
                  key={s.id}
                  type="linear"
                  dataKey={s.id}
                  name={s.name}
                  stroke={seriesColor(s.slot)}
                  strokeWidth={2}
                  dot={(props: { cx?: number; cy?: number; key?: Key }) => (
                    <SeriesDot key={props.key} cx={props.cx} cy={props.cy} slot={s.slot} />
                  )}
                  activeDot={false}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">{title} by season, value and rank per player</caption>
            <thead>
              <tr>
                <th scope="col">Season</th>
                {series.map((s) => (
                  <th key={s.id} scope="col" className="num">
                    <span className="th-player">
                      <Marker slot={s.slot} size={10} /> {s.name}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {seasons.map((season) => (
                <tr key={season}>
                  <td>{season}</td>
                  {series.map((s) => {
                    const p = s.points.find((pt) => pt.season === season)
                    return (
                      <td key={s.id} className="num">
                        {formatValue(p?.stat_value)} <span className="muted">{formatRank(p?.rank)}</span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
