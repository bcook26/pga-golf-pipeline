import { useState } from 'react'

import { usePlayer, usePlayers } from '../api/hooks'
import { useDebounced } from '../lib/useDebounced'
import { MAX_PLAYERS, type Slotted } from '../lib/slots'
import { Marker } from './Marker'

function Chip({ player, onRemove }: { player: Slotted; onRemove: (id: string) => void }) {
  const info = usePlayer(player.id)
  const name = info.data?.display_name ?? player.id
  return (
    <li className="chip">
      <Marker slot={player.slot} />
      <span>{name}</span>
      <button type="button" aria-label={`Remove ${name}`} onClick={() => onRemove(player.id)}>
        ×
      </button>
    </li>
  )
}

export function PlayerPicker({
  selected,
  onAdd,
  onRemove,
}: {
  selected: Slotted[]
  onAdd: (id: string) => void
  onRemove: (id: string) => void
}) {
  const [text, setText] = useState('')
  const term = useDebounced(text.trim())
  const full = selected.length >= MAX_PLAYERS
  const results = usePlayers({ search: term || undefined, has_stats: true, limit: 8 })
  const showResults = term.length >= 2 && !full

  return (
    <div className="picker">
      <ul className="chips" aria-label="Selected players">
        {selected.map((p) => (
          <Chip key={p.id} player={p} onRemove={onRemove} />
        ))}
      </ul>
      <label>
        {full ? `Maximum of ${MAX_PLAYERS} players` : 'Add a player'}
        <input
          type="search"
          value={text}
          disabled={full}
          placeholder="Search by name…"
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      {showResults && results.data && (
        <ul className="results" aria-label="Search results">
          {results.data.items.length === 0 && <li className="status">No players found.</li>}
          {results.data.items.map((p) => {
            const already = selected.some((s) => s.id === p.player_id)
            return (
              <li key={p.player_id}>
                <button
                  type="button"
                  disabled={already}
                  onClick={() => {
                    onAdd(p.player_id)
                    setText('')
                  }}
                >
                  {p.display_name}
                  <span className="muted"> {p.country ?? ''}</span>
                  {already && <span className="muted"> (added)</span>}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
