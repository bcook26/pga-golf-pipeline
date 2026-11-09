/** 1 -> "1st", 22 -> "22nd", 88.3 -> "88th", 11 -> "11th". */
export function ordinal(n: number): string {
  const whole = Math.round(n)
  const lastTwo = whole % 100
  if (lastTwo >= 11 && lastTwo <= 13) return `${whole}th`
  switch (whole % 10) {
    case 1:
      return `${whole}st`
    case 2:
      return `${whole}nd`
    case 3:
      return `${whole}rd`
    default:
      return `${whole}th`
  }
}

export interface Fit {
  slope: number
  intercept: number
  r: number
  n: number
}

/** Least-squares line and Pearson correlation. Null when it is undefined
 *  (fewer than 3 points or no variance on either axis). */
export function linearFit(points: Array<{ x: number; y: number }>): Fit | null {
  const n = points.length
  if (n < 3) return null
  const mx = points.reduce((a, p) => a + p.x, 0) / n
  const my = points.reduce((a, p) => a + p.y, 0) / n
  let sxx = 0
  let syy = 0
  let sxy = 0
  for (const p of points) {
    sxx += (p.x - mx) ** 2
    syy += (p.y - my) ** 2
    sxy += (p.x - mx) * (p.y - my)
  }
  if (sxx === 0 || syy === 0) return null
  const slope = sxy / sxx
  return { slope, intercept: my - slope * mx, r: sxy / Math.sqrt(sxx * syy), n }
}

/** Plain-language strength of a correlation coefficient. */
export function describeCorrelation(r: number): string {
  const a = Math.abs(r)
  const strength = a >= 0.7 ? 'strong' : a >= 0.4 ? 'moderate' : a >= 0.2 ? 'weak' : 'little or no'
  if (a < 0.2) return 'little or no linear relationship'
  return `${strength} ${r > 0 ? 'positive' : 'negative'} relationship`
}

export function formatAge(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '–'
  if (seconds < 90) return 'just now'
  const minutes = seconds / 60
  if (minutes < 90) return `${Math.round(minutes)} min ago`
  const hours = minutes / 60
  if (hours < 36) return `${Math.round(hours)} h ago`
  return `${Math.round(hours / 24)} d ago`
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '–'
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  const m = Math.floor(seconds / 60)
  return `${m} m ${Math.round(seconds - m * 60)} s`
}
