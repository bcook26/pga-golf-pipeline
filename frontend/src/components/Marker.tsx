import { seriesColor, shapePath } from '../lib/series'

/** Series marker used in legends, chips and table headers (colour + shape). */
export function Marker({ slot, size = 12 }: { slot: number; size?: number }) {
  const r = size / 2 - 1
  return (
    <svg width={size} height={size} viewBox={`${-size / 2} ${-size / 2} ${size} ${size}`} aria-hidden="true" focusable="false">
      <path d={shapePath(slot, r)} fill={seriesColor(slot)} />
    </svg>
  )
}
