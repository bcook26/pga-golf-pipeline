import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { mockApi, renderAt } from '../test/helpers'
import { LeadersPage } from './LeadersPage'
import { PlayerPage } from './PlayerPage'
import { PlayersPage } from './PlayersPage'

const seasons = [
  { season: 2025, players: 2, stats: 3, rows: 6 },
  { season: 2024, players: 2, stats: 3, rows: 6 },
]

describe('PlayersPage', () => {
  it('lists players and requests stats-bearing players only', async () => {
    const calls = mockApi([
      ['/seasons', seasons],
      [
        '/players',
        {
          items: [{ player_id: '1', display_name: 'Ada Birdie', is_active: true, country: 'Canada', primary_tour: 'PGA Tour' }],
          total: 1,
          limit: 25,
          offset: 0,
        },
      ],
    ])
    renderAt(<PlayersPage />)
    expect(await screen.findByRole('link', { name: 'Ada Birdie' })).toHaveAttribute('href', '/players/1')
    expect(screen.getByText('1–1 of 1')).toBeInTheDocument()
    expect(calls.some((u) => u.includes('has_stats=true') && u.includes('limit=25'))).toBe(true)
  })

  it('searches after typing (debounced)', async () => {
    const calls = mockApi([
      ['/seasons', seasons],
      ['/players', { items: [], total: 0, limit: 25, offset: 0 }],
    ])
    renderAt(<PlayersPage />)
    await userEvent.type(screen.getByLabelText('Search by name'), 'rahm')
    await waitFor(() => expect(calls.some((u) => u.includes('search=rahm'))).toBe(true))
    expect(await screen.findByText('No players match these filters.')).toBeInTheDocument()
  })

  it('shows an error with retry when the API is down', async () => {
    mockApi([
      ['/seasons', seasons],
      ['/players', [500, { detail: 'boom' }]],
    ])
    renderAt(<PlayersPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not load players/)
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})

describe('PlayerPage', () => {
  const player = {
    player_id: '1',
    display_name: 'Ada Birdie',
    is_active: true,
    country: 'Canada',
    primary_tour: 'PGA Tour',
    bio: { turnedPro: '2018', id: '1' },
    seasons: [2025, 2024],
  }
  const stat = (id: string, name: string, cats: string[]) => ({
    season: 2025, stat_id: id, stat_name: name, stat_value: 1.5, rank: 3,
    categories: cats, supporting_stat: null, supporting_value: null, details: null,
  })

  it('shows profile, stats for the latest season and filters by category', async () => {
    mockApi([
      ['/players/1', player],
      ['/players/1/stats?', [stat('02675', 'SG: Total', ['STROKES_GAINED']), stat('02564', 'SG: Putting', ['PUTTING'])]],
      [
        '/history',
        { player_id: '1', stat_id: '02675', stat_name: 'SG: Total', points: [{ season: 2024, stat_value: 1, rank: 5 }, { season: 2025, stat_value: 1.5, rank: 3 }] },
      ],
    ])
    renderAt(
      <Routes>
        <Route path="/players/:id" element={<PlayerPage />} />
      </Routes>,
      '/players/1',
    )
    expect(await screen.findByRole('heading', { name: 'Ada Birdie' })).toBeInTheDocument()
    expect(screen.getByText('Turned Pro')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'SG: Putting' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'SG: Total by season' })).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'PUTTING')
    expect(screen.queryByRole('button', { name: 'SG: Total' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'SG: Putting' })).toBeInTheDocument()
  })

  it('reports an unknown player', async () => {
    mockApi([['/players/NOPE', [404, { detail: 'Player NOPE not found' }]]])
    renderAt(
      <Routes>
        <Route path="/players/:id" element={<PlayerPage />} />
      </Routes>,
      '/players/NOPE',
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Not found: Player NOPE not found')
  })
})

describe('LeadersPage', () => {
  it('renders the leaderboard for the default stat', async () => {
    const calls = mockApi([
      ['/seasons', seasons],
      ['/stats?', [{ stat_id: '02675', stat_name: 'SG: Total', categories: ['STROKES_GAINED'] }]],
      [
        '/leaders',
        { stat_id: '02675', stat_name: 'SG: Total', season: 2025, rows: [{ rank: 1, player_id: '1', player_name: 'Ada Birdie', stat_value: 2.5, supporting_stat: null, supporting_value: null }] },
      ],
    ])
    renderAt(<LeadersPage />)
    expect(await screen.findByRole('heading', { name: 'SG: Total · 2025' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ada Birdie' })).toBeInTheDocument()
    expect(calls.some((u) => u.includes('/stats/02675/leaders') && u.includes('limit=25'))).toBe(true)
  })
})
