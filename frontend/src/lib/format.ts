const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 })

export function formatValue(value: number | null | undefined): string {
  return value === null || value === undefined ? '–' : number.format(value)
}

export function formatRank(rank: number | null | undefined): string {
  return rank === null || rank === undefined ? '–' : `#${rank}`
}

export function titleCase(token: string): string {
  return token
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}
