/**
 * Selected players live in the URL as repeated `p=<slot>:<playerId>` params.
 * The slot picks the player's colour and marker shape, so a player keeps both
 * when another player is removed (colour follows the entity, not its position).
 */
export const MAX_PLAYERS = 4

export interface Slotted {
  slot: number
  id: string
}

export function parseSlots(values: string[]): Slotted[] {
  const used = new Set<number>()
  const seen = new Set<string>()
  const out: Slotted[] = []
  const pending: string[] = []
  for (const raw of values) {
    const m = /^([0-3]):(.+)$/.exec(raw)
    if (!m) {
      pending.push(raw) // hand-typed `p=<id>`: assign a slot below
      continue
    }
    const slot = Number(m[1])
    const id = m[2] as string
    if (used.has(slot) || seen.has(id)) continue
    used.add(slot)
    seen.add(id)
    out.push({ slot, id })
  }
  for (const id of pending) {
    if (seen.has(id)) continue
    const slot = firstFreeSlot(used)
    if (slot === null) break
    used.add(slot)
    seen.add(id)
    out.push({ slot, id })
  }
  return out.slice(0, MAX_PLAYERS)
}

export function firstFreeSlot(used: Set<number>): number | null {
  for (let slot = 0; slot < MAX_PLAYERS; slot++) if (!used.has(slot)) return slot
  return null
}

export function serializeSlots(players: Slotted[]): string[] {
  return players.map((p) => `${p.slot}:${p.id}`)
}

export function addPlayer(players: Slotted[], id: string): Slotted[] {
  if (players.some((p) => p.id === id)) return players
  const slot = firstFreeSlot(new Set(players.map((p) => p.slot)))
  return slot === null ? players : [...players, { slot, id }]
}

export function removePlayer(players: Slotted[], id: string): Slotted[] {
  return players.filter((p) => p.id !== id)
}
