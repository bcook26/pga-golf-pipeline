import { describe, expect, it } from 'vitest'

import type { CompareStat } from '../api/client'
import { bestPlayerIds } from './compare'

const stat = (ranks: Array<number | null | undefined>): CompareStat => ({
  stat_id: 's',
  stat_name: 'S',
  categories: [],
  values: ranks.map((rank, i) =>
    rank === undefined ? null : { player_id: `p${i}`, stat_value: 1, rank },
  ),
})

describe('bestPlayerIds', () => {
  it('picks the lowest rank, regardless of stat direction', () => {
    expect([...bestPlayerIds(stat([5, 2, 9]))]).toEqual(['p1'])
  })
  it('highlights ties', () => {
    expect([...bestPlayerIds(stat([3, 3, 9]))].sort()).toEqual(['p0', 'p1'])
  })
  it('highlights nothing with fewer than two ranked players', () => {
    expect(bestPlayerIds(stat([4, null, undefined])).size).toBe(0)
  })
})
