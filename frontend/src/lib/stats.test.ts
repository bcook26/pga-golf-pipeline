import { describe, expect, it } from 'vitest'

import { describeCorrelation, formatAge, formatDuration, linearFit, ordinal } from './stats'

describe('ordinal', () => {
  it.each([
    [1, '1st'], [2, '2nd'], [3, '3rd'], [4, '4th'], [11, '11th'], [12, '12th'], [13, '13th'],
    [21, '21st'], [22, '22nd'], [88.3, '88th'], [99.6, '100th'], [0, '0th'],
  ])('%s -> %s', (n, expected) => expect(ordinal(n)).toBe(expected))
})

describe('linearFit', () => {
  it('recovers a perfect line', () => {
    const fit = linearFit([{ x: 1, y: 3 }, { x: 2, y: 5 }, { x: 3, y: 7 }])
    expect(fit?.slope).toBeCloseTo(2)
    expect(fit?.intercept).toBeCloseTo(1)
    expect(fit?.r).toBeCloseTo(1)
  })
  it('is negative for inverse relationships', () => {
    expect(linearFit([{ x: 1, y: 9 }, { x: 2, y: 5 }, { x: 3, y: 1 }])?.r).toBeCloseTo(-1)
  })
  it('is undefined with too few points or no variance', () => {
    expect(linearFit([{ x: 1, y: 1 }, { x: 2, y: 2 }])).toBeNull()
    expect(linearFit([{ x: 1, y: 1 }, { x: 1, y: 2 }, { x: 1, y: 3 }])).toBeNull()
  })
})

describe('describeCorrelation', () => {
  it('uses plain language', () => {
    expect(describeCorrelation(0.85)).toBe('strong positive relationship')
    expect(describeCorrelation(-0.5)).toBe('moderate negative relationship')
    expect(describeCorrelation(0.25)).toBe('weak positive relationship')
    expect(describeCorrelation(0.05)).toBe('little or no linear relationship')
  })
})

describe('time formatting', () => {
  it('formats ages', () => {
    expect(formatAge(30)).toBe('just now')
    expect(formatAge(20 * 60)).toBe('20 min ago')
    expect(formatAge(5 * 3600)).toBe('5 h ago')
    expect(formatAge(72 * 3600)).toBe('3 d ago')
    expect(formatAge(null)).toBe('–')
  })
  it('formats durations', () => {
    expect(formatDuration(4.25)).toBe('4.3 s')
    expect(formatDuration(125)).toBe('2 m 5 s')
    expect(formatDuration(undefined)).toBe('–')
  })
})
