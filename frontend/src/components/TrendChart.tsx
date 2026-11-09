import { useState } from 'react'
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

export interface TrendPoint {
  season: number
  stat_value: number | null
  rank: number | null
}

interface TooltipProps {
  active?: boolean
  payload?: ReadonlyArray<{ payload: TrendPoint }>
}

function ChartTooltip({ active, payload }: TooltipProps) {
  const point = active ? payload?.[0]?.payload : undefined
  if (!point) return null
  return (
    <div className="chart-tooltip">
      <strong>{point.season}</strong>
      <div>Value: {formatValue(point.stat_value)}</div>
      <div>Rank: {formatRank(point.rank)}</div>
    </div>
  )
}

/**
 * Single-series trend of one stat across seasons. Value is the only axis;
 * rank is shown in the tooltip and table (never a second y-scale).
 * A table view gives the same data without relying on colour or hover.
 */
export function TrendChart({ title, points }: { title: string; points: TrendPoint[] }) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const summary = points
    .map((p) => `${p.season}: ${formatValue(p.stat_value)} (rank ${formatRank(p.rank)})`)
    .join('; ')

  return (
    <section className="card" aria-label={`${title} by season`}>
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

      {view === 'chart' ? (
        <div className="chart" role="img" aria-label={`${title} by season. ${summary}`}>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={points} margin={{ top: 12, right: 24, bottom: 4, left: 0 }}>
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
                content={<ChartTooltip />}
                offset={24}
                cursor={{ stroke: 'var(--grid-strong)', strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="stat_value"
                stroke="var(--series-1)"
                strokeWidth={2}
                dot={{ r: 4, fill: 'var(--series-1)', stroke: 'var(--surface-1)', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: 'var(--series-1)', stroke: 'var(--surface-1)', strokeWidth: 2 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <table>
          <caption className="sr-only">{title} by season</caption>
          <thead>
            <tr>
              <th scope="col">Season</th>
              <th scope="col" className="num">
                Value
              </th>
              <th scope="col" className="num">
                Rank
              </th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.season}>
                <td>{p.season}</td>
                <td className="num">{formatValue(p.stat_value)}</td>
                <td className="num">{formatRank(p.rank)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
