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

/** Strokes relative to par as golf shows it: -18, E, +3. */
export function formatToPar(toPar: number | null | undefined): string {
  if (toPar === null || toPar === undefined) return '–'
  if (toPar === 0) return 'E'
  return toPar > 0 ? `+${toPar}` : `−${Math.abs(toPar)}`
}

const dollars = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

/** Whole dollars ($1,800,000); '–' when unknown. */
export function formatMoney(amount: number | null | undefined): string {
  return amount === null || amount === undefined ? '–' : dollars.format(amount)
}

/** $20M / $8.7M / $950K for tight columns; full amount belongs in a title. */
export function formatMoneyShort(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '–'
  if (amount >= 1_000_000) return `$${+(amount / 1_000_000).toFixed(2)}M`
  if (amount >= 1_000) return `$${Math.round(amount / 1_000)}K`
  return `$${amount}`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** 'YYYY-MM-DD' -> 'Jan 2, 2025'. Parsed by hand so time zones cannot shift the day. */
export function formatDate(iso: string | null | undefined): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '')
  if (!m) return '–'
  return `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}`
}

/** FedExCup points: tied finishers split points, so 266.667 -> 266.7. */
export function formatPoints(points: number | null | undefined): string {
  return points === null || points === undefined ? '–' : String(+points.toFixed(1))
}
