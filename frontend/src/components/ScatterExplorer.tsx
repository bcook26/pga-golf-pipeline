import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { Scatter as ScatterData, ScatterPoint } from '../api/client'
import { formatRank, formatValue } from '../lib/format'
import { seriesColor, shapePath } from '../lib/series'
import { describeCorrelation, linearFit } from '../lib/stats'
import { Marker } from './Marker'

export interface Highlight {
  id: string
  name: string
  slot: number
}

const padded = ([min, max]: [number, number]): [number, number] => {
  const pad = (max - min) * 0.05 || 1
  return [Math.floor(min - pad), Math.ceil(max + pad)]
}

type Shape = (props: { cx?: number; cy?: number }) => React.ReactElement

const baseShape: Shape = ({ cx, cy }) =>
  cx === undefined || cy === undefined ? <g /> : <circle cx={cx} cy={cy} r={3.5} fill="var(--neutral-point)" fillOpacity={0.55} />

const highlightShape =
  (slot: number): Shape =>
  ({ cx, cy }) =>
    cx === undefined || cy === undefined ? (
      <g />
    ) : (
      <path transform={`translate(${cx},${cy})`} d={shapePath(slot, 6)} fill={seriesColor(slot)} stroke="var(--surface-1)" strokeWidth={2} />
    )

function PointTooltip({ active, payload, data }: { active?: boolean; payload?: ReadonlyArray<{ payload: ScatterPoint }>; data: ScatterData }) {
  const p = active ? payload?.[0]?.payload : undefined
  if (!p) return null
  return (
    <div className="chart-tooltip">
      <strong>{p.player_name ?? p.player_id}</strong>
      <div>
        {data.x.stat_name}: {formatValue(p.x)} ({formatRank(p.rank_x)})
      </div>
      <div>
        {data.y.stat_name}: {formatValue(p.y)} ({formatRank(p.rank_y)})
      </div>
    </div>
  )
}

/**
 * One point per player for two stats. All players are a neutral grey; at most
 * three chosen players are highlighted (colour + shape + name label), which is
 * the series cap for scatter plots. The dashed line is the least-squares fit.
 */
export function ScatterExplorer({ data, highlights }: { data: ScatterData; highlights: Highlight[] }) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const byId = useMemo(() => new Map(data.points.map((p) => [p.player_id, p])), [data.points])
  const highlightedIds = new Set(highlights.map((h) => h.id))
  const base = useMemo(() => data.points.filter((p) => !highlightedIds.has(p.player_id)), [data.points, highlights]) // eslint-disable-line react-hooks/exhaustive-deps
  const fit = useMemo(() => linearFit(data.points), [data.points])

  const xs = data.points.map((p) => p.x)
  const segment =
    fit &&
    ([
      { x: Math.min(...xs), y: fit.intercept + fit.slope * Math.min(...xs) },
      { x: Math.max(...xs), y: fit.intercept + fit.slope * Math.max(...xs) },
    ] as const)

  const missing = highlights.filter((h) => !byId.has(h.id))
  const title = `${data.y.stat_name} vs ${data.x.stat_name}, ${data.season}`

  return (
    <section className="card" aria-label={title}>
      <header className="card-header">
        <h3>{title}</h3>
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
        <li>
          <svg width="12" height="12" viewBox="-6 -6 12 12" aria-hidden="true">
            <circle r="4" fill="var(--neutral-point)" fillOpacity="0.55" />
          </svg>
          <span>All players ({data.points.length})</span>
        </li>
        {highlights.map((h) => (
          <li key={h.id}>
            <Marker slot={h.slot} />
            <span>{h.name}</span>
            {!byId.has(h.id) && <span className="muted">no data for this pair</span>}
          </li>
        ))}
      </ul>
      {fit && (
        <p className="muted corr">
          Correlation r = {fit.r.toFixed(2)} across {fit.n} players: {describeCorrelation(fit.r)}.
        </p>
      )}
      {missing.length > 0 && <p className="muted">Some highlighted players have no value for both stats this season.</p>}

      {view === 'chart' ? (
        <div className="chart" role="img" aria-label={`Scatter plot: ${title}. ${fit ? `Correlation ${fit.r.toFixed(2)}.` : ''}`}>
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ top: 16, right: 24, bottom: 24, left: 8 }}>
              <CartesianGrid stroke="var(--grid)" />
              <XAxis
                type="number"
                dataKey="x"
                name={data.x.stat_name ?? 'x'}
                domain={padded}
                tickLine={false}
                axisLine={{ stroke: 'var(--grid-strong)' }}
                tickFormatter={(v: number) => formatValue(v)}
                label={{ value: data.x.stat_name ?? '', position: 'insideBottom', offset: -12, fill: 'var(--text-secondary)' }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={data.y.stat_name ?? 'y'}
                domain={padded}
                tickLine={false}
                axisLine={false}
                width={56}
                tickFormatter={(v: number) => formatValue(v)}
                label={{ value: data.y.stat_name ?? '', angle: -90, position: 'insideLeft', offset: 8, fill: 'var(--text-secondary)', style: { textAnchor: 'middle' } }}
              />
              <Tooltip cursor={{ strokeDasharray: '3 3', stroke: 'var(--grid-strong)' }} content={<PointTooltip data={data} />} />
              <Scatter data={base} shape={baseShape as never} isAnimationActive={false} />
              {segment && <ReferenceLine segment={[...segment]} stroke="var(--text-muted)" strokeDasharray="6 4" strokeWidth={1.5} />}
              {highlights.map((h) => {
                const point = byId.get(h.id)
                return point ? (
                  <Scatter key={h.id} data={[point]} shape={highlightShape(h.slot) as never} isAnimationActive={false}>
                    <LabelList dataKey="player_name" position="top" offset={10} className="scatter-label" />
                  </Scatter>
                ) : null
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="table-scroll tall">
          <table>
            <caption className="sr-only">{title}: value and rank per player</caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col" className="num">{data.x.stat_name}</th>
                <th scope="col" className="num">{data.y.stat_name}</th>
              </tr>
            </thead>
            <tbody>
              {data.points.map((p) => (
                <tr key={p.player_id}>
                  <td>{p.player_name ?? p.player_id}</td>
                  <td className="num">{formatValue(p.x)} <span className="muted">{formatRank(p.rank_x)}</span></td>
                  <td className="num">{formatValue(p.y)} <span className="muted">{formatRank(p.rank_y)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
