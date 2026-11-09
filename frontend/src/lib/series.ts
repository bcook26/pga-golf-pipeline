/** Series identity = colour + marker shape, so it never relies on colour alone. */
export const SHAPES = ['circle', 'square', 'diamond', 'triangle'] as const

export function seriesColor(slot: number): string {
  return `var(--series-${slot + 1})`
}

export function shapePath(slot: number, r: number): string {
  switch (SHAPES[slot % SHAPES.length]) {
    case 'square':
      return `M${-r},${-r}h${2 * r}v${2 * r}h${-2 * r}z`
    case 'diamond':
      return `M0,${-r * 1.25}L${r * 1.25},0L0,${r * 1.25}L${-r * 1.25},0z`
    case 'triangle':
      return `M0,${-r * 1.2}L${r * 1.1},${r * 0.9}L${-r * 1.1},${r * 0.9}z`
    default:
      return `M${-r},0a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0z`
  }
}
