import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { mockApi, renderAt } from '../test/helpers'
import { StatsPage } from './StatsPage'

const catalogue = [
  { stat_id: '02675', stat_name: 'SG: Total', categories: ['STROKES_GAINED'] },
  { stat_id: '101', stat_name: 'Driving Distance', categories: ['OFF_THE_TEE'] },
]
const common: Array<[string, unknown]> = [
  ['/stats?', catalogue],
  ['/seasons', [{ season: 2026 }, { season: 2025 }]],
]

const page = () => (
  <Routes>
    <Route path="/stats" element={<StatsPage />} />
  </Routes>
)

describe('StatsPage', () => {
  it('prompts for a player on the profile tab', async () => {
    mockApi(common)
    renderAt(page(), '/stats')
    expect(await screen.findByText(/choose a player to see/i)).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Percentile profile' })).toHaveAttribute('aria-selected', 'true')
  })

  it('shows percentile rows with text values', async () => {
    mockApi([
      ...common,
      ['/players/P1', { player_id: 'P1', display_name: 'Test Player' }],
      ['/players/P1/percentiles', {
        player_id: 'P1', display_name: 'Test Player', season: 2026,
        stats: [{ stat_id: '02675', stat_name: 'SG: Total', rank: 22, field_size: 180, percentile: 88, stat_value: 1.2, categories: ['STROKES_GAINED'] }],
      }],
    ])
    renderAt(page(), '/stats?player=P1')
    expect(await screen.findByText(/#22 of 180/)).toBeInTheDocument()
    expect(screen.getByText('88th')).toBeInTheDocument()
  })

  it('renders movers with places gained and the in-progress note', async () => {
    mockApi([
      ...common,
      ['/movers', {
        stat_id: '02675', stat_name: 'SG: Total', season: 2026, compare_to: 2025, players_compared: 133,
        improvers: [{ player_id: 'A', player_name: 'Alpha', rank_from: 118, rank_to: 26, rank_change: 92, value_from: -0.1, value_to: 0.5 }],
        decliners: [{ player_id: 'B', player_name: 'Beta', rank_from: 10, rank_to: 90, rank_change: -80, value_from: 0.9, value_to: 0.0 }],
      }],
    ])
    renderAt(page(), '/stats?tab=movers')
    expect(await screen.findByText(/#118 → #26/)).toBeInTheDocument()
    expect(screen.getByText(/#10 → #90/)).toBeInTheDocument()
    expect(screen.getByText(/games played so far/i)).toBeInTheDocument()
  })

  it('switches tabs and resets filters', async () => {
    mockApi(common)
    renderAt(page(), '/stats')
    await userEvent.click(screen.getByRole('tab', { name: 'Scatter explorer' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Scatter explorer' })).toHaveAttribute('aria-selected', 'true'))
    expect(screen.getByLabelText('X axis')).toBeInTheDocument()
  })

  it('refuses identical scatter axes', async () => {
    mockApi(common)
    renderAt(page(), '/stats?tab=scatter&x=101&y=101')
    expect(await screen.findByText(/two different stats/i)).toBeInTheDocument()
  })
})
