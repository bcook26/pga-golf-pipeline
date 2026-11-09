import type { CompareStat } from '../api/client'

/** Players holding the best (lowest) rank in this row. Rank is direction-agnostic:
 *  #1 is best whether the stat is "higher is better" or "lower is better". */
export function bestPlayerIds(stat: CompareStat): Set<string> {
  const ranked = stat.values.filter((v) => v?.rank !== null && v?.rank !== undefined)
  if (ranked.length < 2) return new Set()
  const best = Math.min(...ranked.map((v) => v?.rank as number))
  return new Set(ranked.filter((v) => v?.rank === best).map((v) => v?.player_id as string))
}
