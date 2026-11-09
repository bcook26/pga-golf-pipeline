import { describe, expect, it } from 'vitest'

import { addPlayer, parseSlots, removePlayer, serializeSlots } from './slots'

describe('player slots', () => {
  it('parses slot-prefixed ids and assigns slots to plain ids', () => {
    expect(parseSlots(['2:b', 'a', '0:c'])).toEqual([
      { slot: 2, id: 'b' },
      { slot: 0, id: 'c' },
      { slot: 1, id: 'a' }, // first free slot
    ])
  })

  it('ignores duplicates and caps at four', () => {
    expect(parseSlots(['0:a', '0:b', '1:a'])).toEqual([{ slot: 0, id: 'a' }])
    expect(parseSlots(['a', 'b', 'c', 'd', 'e'])).toHaveLength(4)
  })

  it('keeps survivors on their slot when a player is removed, and reuses the freed slot', () => {
    let players = parseSlots(['0:a', '1:b', '2:c'])
    players = removePlayer(players, 'a')
    expect(players.map((p) => p.slot)).toEqual([1, 2]) // b and c keep their colours
    players = addPlayer(players, 'd')
    expect(players).toContainEqual({ slot: 0, id: 'd' })
    expect(serializeSlots(players)).toEqual(['1:b', '2:c', '0:d'])
  })

  it('does not add a fifth player or a duplicate', () => {
    const four = parseSlots(['a', 'b', 'c', 'd'])
    expect(addPlayer(four, 'e')).toEqual(four)
    expect(addPlayer(four, 'a')).toEqual(four)
  })
})
