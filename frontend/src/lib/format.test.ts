import { describe, expect, it } from 'vitest'

import { formatDate, formatMoney, formatMoneyShort, formatPoints, formatToPar } from './format'

describe('formatToPar', () => {
  it('shows golf notation', () => {
    expect(formatToPar(0)).toBe('E')
    expect(formatToPar(3)).toBe('+3')
    expect(formatToPar(-18)).toBe('−18')
    expect(formatToPar(null)).toBe('–')
  })
})

describe('money', () => {
  it('formats whole dollars and short forms', () => {
    expect(formatMoney(1800000)).toBe('$1,800,000')
    expect(formatMoney(undefined)).toBe('–')
    expect(formatMoneyShort(20_000_000)).toBe('$20M')
    expect(formatMoneyShort(8_700_000)).toBe('$8.7M')
    expect(formatMoneyShort(950_000)).toBe('$950K')
    expect(formatMoneyShort(0)).toBe('$0')
  })
})

describe('formatDate', () => {
  it('does not shift the day across time zones', () => {
    expect(formatDate('2025-01-02')).toBe('Jan 2, 2025')
    expect(formatDate('2025-12-31')).toBe('Dec 31, 2025')
    expect(formatDate(null)).toBe('–')
    expect(formatDate('nope')).toBe('–')
  })
})

describe('formatPoints', () => {
  it('rounds split points to one decimal', () => {
    expect(formatPoints(266.667)).toBe('266.7')
    expect(formatPoints(700)).toBe('700')
    expect(formatPoints(12.5)).toBe('12.5')
    expect(formatPoints(null)).toBe('–')
  })
})
