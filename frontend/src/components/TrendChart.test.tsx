import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { TrendChart } from './TrendChart'

const points = [
  { season: 2024, stat_value: 2.496, rank: 1 },
  { season: 2025, stat_value: null, rank: null },
]

describe('TrendChart', () => {
  it('describes the data for assistive tech', () => {
    render(<TrendChart title="SG: Total" points={points} />)
    expect(screen.getByRole('img')).toHaveAccessibleName(/2024: 2.496 \(rank #1\); 2025: – \(rank –\)/)
  })

  it('offers a table view of the same data', async () => {
    render(<TrendChart title="SG: Total" points={points} />)
    await userEvent.click(screen.getByRole('button', { name: 'Table' }))
    expect(screen.getByRole('cell', { name: '2.496' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '#1' })).toBeInTheDocument()
    expect(screen.getAllByRole('cell', { name: '–' })).toHaveLength(2)
  })
})
