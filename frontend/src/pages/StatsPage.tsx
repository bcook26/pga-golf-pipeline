import { Suspense, lazy, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useMovers, usePercentiles, useScatter, useSeasons } from '../api/hooks'
import { MoversChart } from '../components/MoversChart'
import { PercentileProfile } from '../components/PercentileProfile'
import { PlayerPicker } from '../components/PlayerPicker'
import { QueryStatus } from '../components/QueryStatus'
import { StatSelect } from '../components/StatSelect'
import { titleCase } from '../lib/format'
import { addPlayer, parseSlots, removePlayer, serializeSlots } from '../lib/slots'

// Recharts is large; load it only when the scatter tab is shown.
const ScatterExplorer = lazy(() =>
  import('../components/ScatterExplorer').then((m) => ({ default: m.ScatterExplorer })),
)

const TABS = [
  { id: 'profile', label: 'Percentile profile' },
  { id: 'movers', label: 'Improvers & decliners' },
  { id: 'scatter', label: 'Scatter explorer' },
] as const
type TabId = (typeof TABS)[number]['id']

const CATEGORIES = ['STROKES_GAINED', 'OFF_THE_TEE', 'APPROACH', 'AROUND_THE_GREEN', 'PUTTING', 'SCORING']
const MAX_HIGHLIGHTS = 3

type Update = (mutate: (sp: URLSearchParams) => void) => void

function setOrDelete(sp: URLSearchParams, key: string, value: string | null) {
  if (value) sp.set(key, value)
  else sp.delete(key)
}

function SeasonSelect({ value, onChange }: { value: number | undefined; onChange: (s: string) => void }) {
  const seasons = useSeasons()
  return (
    <label>
      Season
      <select value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
        {seasons.data?.map((s) => (
          <option key={s.season} value={s.season}>
            {s.season}
          </option>
        ))}
      </select>
    </label>
  )
}

function ProfileTab({ params, update }: { params: URLSearchParams; update: Update }) {
  const playerId = params.get('player') ?? undefined
  const category = params.get('category') ?? 'STROKES_GAINED'
  const season = params.get('season') ? Number(params.get('season')) : undefined
  const profile = usePercentiles(playerId, { season, category })
  const selected = playerId ? [{ slot: 0, id: playerId }] : []

  return (
    <>
      <PlayerPicker
        selected={selected}
        max={1}
        markers={false}
        label="Choose a player"
        onAdd={(id) => update((sp) => setOrDelete(sp, 'player', id))}
        onRemove={() => update((sp) => setOrDelete(sp, 'player', null))}
      />
      {!playerId ? (
        <p className="status">Choose a player to see where they rank against the field.</p>
      ) : (
        <>
          <form className="filters" onSubmit={(e) => e.preventDefault()}>
            <SeasonSelect value={season ?? profile.data?.season} onChange={(s) => update((sp) => setOrDelete(sp, 'season', s))} />
            <div className="chips" role="group" aria-label="Category">
              {CATEGORIES.map((c) => (
                <button key={c} type="button" className="chip-toggle" aria-pressed={c === category} onClick={() => update((sp) => setOrDelete(sp, 'category', c))}>
                  {titleCase(c)}
                </button>
              ))}
            </div>
          </form>
          <QueryStatus query={profile} what="percentiles" />
          {profile.data && (
            <section className="card" aria-label="Percentile profile">
              <h3>
                {profile.data.display_name} · {titleCase(category)} · {profile.data.season}
              </h3>
              {profile.data.stats.length === 0 ? (
                <p className="status">No ranked stats in this category.</p>
              ) : (
                <PercentileProfile stats={profile.data.stats} />
              )}
            </section>
          )}
        </>
      )}
    </>
  )
}

function MoversTab({ params, update }: { params: URLSearchParams; update: Update }) {
  const statId = params.get('stat') ?? '02675'
  const limit = Number(params.get('limit') ?? 10)
  const seasons = useSeasons()
  const latest = seasons.data?.[0]?.season
  const season = params.get('season') ? Number(params.get('season')) : latest
  const movers = useMovers(statId, { season, compare_to: season ? season - 1 : undefined, limit })

  return (
    <>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <StatSelect label="Stat" value={statId} onChange={(id) => update((sp) => setOrDelete(sp, 'stat', id))} />
        <SeasonSelect value={season} onChange={(s) => update((sp) => setOrDelete(sp, 'season', s))} />
        <label>
          Show
          <select value={limit} onChange={(e) => update((sp) => setOrDelete(sp, 'limit', e.target.value))}>
            {[5, 10, 15, 25].map((n) => (
              <option key={n} value={n}>
                Top {n} each way
              </option>
            ))}
          </select>
        </label>
      </form>
      <QueryStatus query={movers} what="movers" />
      {movers.data && (
        <section className="card" aria-label="Improvers and decliners">
          <h3>
            {movers.data.stat_name}: rank change {movers.data.compare_to} → {movers.data.season}
          </h3>
          <p className="muted">
            Blue bars climbed the rankings, red bars fell. {movers.data.players_compared} players ranked in both seasons.
            {season === latest && ' The latest season is in progress, so it reflects games played so far.'}
          </p>
          <MoversChart movers={movers.data} />
        </section>
      )}
    </>
  )
}

function ScatterTab({ params, update }: { params: URLSearchParams; update: Update }) {
  const x = params.get('x') ?? '101'
  const y = params.get('y') ?? '102'
  const season = params.get('season') ? Number(params.get('season')) : undefined
  const highlights = useMemo(() => parseSlots(params.getAll('p')).slice(0, MAX_HIGHLIGHTS), [params])
  const scatter = useScatter({ x, y, season })

  function setPlayers(next: typeof highlights) {
    update((sp) => {
      sp.delete('p')
      for (const v of serializeSlots(next)) sp.append('p', v)
    })
  }

  return (
    <>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <StatSelect label="X axis" value={x} onChange={(id) => update((sp) => setOrDelete(sp, 'x', id))} />
        <StatSelect label="Y axis" value={y} onChange={(id) => update((sp) => setOrDelete(sp, 'y', id))} />
        <SeasonSelect value={season ?? scatter.data?.season} onChange={(s) => update((sp) => setOrDelete(sp, 'season', s))} />
      </form>
      <PlayerPicker
        selected={highlights}
        max={MAX_HIGHLIGHTS}
        label="Highlight a player"
        onAdd={(id) => setPlayers(addPlayer(highlights, id))}
        onRemove={(id) => setPlayers(removePlayer(highlights, id))}
      />
      {x === y && <p className="status">Choose two different stats.</p>}
      <QueryStatus query={scatter} what="scatter data" />
      {scatter.data && x !== y && (
        <Suspense fallback={<p className="status">Loading chart…</p>}>
          <HighlightedScatter data={scatter.data} highlights={highlights} />
        </Suspense>
      )}
    </>
  )
}

function HighlightedScatter({
  data,
  highlights,
}: {
  data: NonNullable<ReturnType<typeof useScatter>['data']>
  highlights: { id: string; slot: number }[]
}) {
  // Names come from the player cache; points carry names for everyone plotted.
  const names = new Map(data.points.map((p) => [p.player_id, p.player_name ?? p.player_id]))
  return (
    <ScatterExplorer
      data={data}
      highlights={highlights.map((h) => ({ ...h, name: names.get(h.id) ?? h.id }))}
    />
  )
}

export function StatsPage() {
  const [params, setParams] = useSearchParams()
  const update: Update = (mutate) => {
    const sp = new URLSearchParams(params)
    mutate(sp)
    setParams(sp, { replace: true })
  }
  const tab = (TABS.find((t) => t.id === params.get('tab'))?.id ?? 'profile') as TabId

  // Switching tabs keeps only the tab itself, so filters don't leak across views.
  function selectTab(id: TabId) {
    setParams(id === 'profile' ? {} : { tab: id }, { replace: true })
  }

  return (
    <>
      <h1>Stats</h1>
      <p className="muted">Explore how players rank, how rankings changed, and how stats relate.</p>
      <div className="tabs" role="tablist" aria-label="Stats views">
        {TABS.map((t) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            type="button"
            role="tab"
            aria-selected={t.id === tab}
            aria-controls="stats-panel"
            onClick={() => selectTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div id="stats-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'profile' && <ProfileTab params={params} update={update} />}
        {tab === 'movers' && <MoversTab params={params} update={update} />}
        {tab === 'scatter' && <ScatterTab params={params} update={update} />}
      </div>
    </>
  )
}
