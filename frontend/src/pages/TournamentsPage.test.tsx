import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { mockApi, renderAt } from '../test/helpers'
import { PlayerPage } from './PlayerPage'
import { TournamentPage } from './TournamentPage'
import { TournamentsPage } from './TournamentsPage'

const seasons = [{ season: 2025, players: 2, stats: 3, rows: 6 }]

const summary = {
  tournament_id: 'R2025016',
  season: 2025,
  name: 'The Sentry',
  start_date: '2025-01-02',
  course_name: 'Plantation Course',
  city: 'Kapalua',
  state_code: 'HI',
  country_code: 'USA',
  purse_usd: 20_000_000,
  status: 'completed',
  category: 'SIGNATURE',
  winner_id: '32839',
  winner_name: 'Hideki Matsuyama',
  winning_to_par: -35,
  field_size: 59,
}

const result = (over: Record<string, unknown>) => ({
  player_id: '1',
  player_name: 'Ada Birdie',
  position_text: '1',
  position: 1,
  is_tied: false,
  status: 'finished',
  total_score: 257,
  to_par: -35,
  rounds: [65, 65, 62, 65],
  fedex_points: 700,
  earnings_usd: 3_600_000,
  ...over,
})

describe('TournamentsPage', () => {
  it('lists tournaments with winner, score and purse', async () => {
    const calls = mockApi([
      ['/seasons', seasons],
      [
        '/tournaments',
        [
          summary,
          { ...summary, tournament_id: 'R2', name: 'Future Open', winner_id: null, winner_name: null, winning_to_par: null, field_size: 0, status: 'upcoming', category: null },
        ],
      ],
    ])
    renderAt(<TournamentsPage />)
    expect(await screen.findByRole('link', { name: 'The Sentry' })).toHaveAttribute('href', '/tournaments/R2025016')
    expect(screen.getByRole('link', { name: 'Hideki Matsuyama' })).toHaveAttribute('href', '/players/32839')
    expect(screen.getByText('−35')).toBeInTheDocument()
    expect(screen.getAllByText('$20M')).toHaveLength(2)
    expect(screen.getByText('Signature')).toBeInTheDocument()
    // upcoming events show their status, and do not link to an empty results page
    expect(screen.getByText('Upcoming')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Future Open' })).not.toBeInTheDocument()
    await waitFor(() => expect(calls.some((u) => u.includes('/tournaments') && u.includes('season=2025'))).toBe(true))
  })

  it('shows an empty state', async () => {
    mockApi([['/seasons', seasons], ['/tournaments', []]])
    renderAt(<TournamentsPage />)
    expect(await screen.findByText(/no tournaments match/i)).toBeInTheDocument()
  })
})

describe('TournamentPage', () => {
  const detail = {
    ...summary,
    results: [
      result({}),
      result({ player_id: '2', player_name: 'Cy Cut', position_text: 'CUT', position: null, status: 'cut', total_score: 150, to_par: 6, rounds: [75, 75, null, null], fedex_points: 0, earnings_usd: 0 }),
    ],
  }
  const page = () => (
    <Routes>
      <Route path="/tournaments/:id" element={<TournamentPage />} />
    </Routes>
  )

  it('shows results with rounds, cut players and a filter', async () => {
    mockApi([['/tournaments/R2025016', detail]])
    renderAt(page(), '/tournaments/R2025016')
    expect(await screen.findByRole('heading', { name: 'The Sentry' })).toBeInTheDocument()
    expect(screen.getByText('CUT')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ada Birdie' })).toHaveAttribute('href', '/players/1')

    await userEvent.click(screen.getByLabelText(/include missed cut/i))
    expect(screen.queryByText('Cy Cut')).not.toBeInTheDocument()
    await userEvent.click(screen.getByLabelText(/include missed cut/i))
    await userEvent.type(screen.getByLabelText('Find player'), 'cy')
    expect(screen.queryByText('Ada Birdie')).not.toBeInTheDocument()
    expect(screen.getByText('Cy Cut')).toBeInTheDocument()
  })

  it('reports an unknown tournament', async () => {
    mockApi([['/tournaments/NOPE', [404, { detail: 'Tournament NOPE not found' }]]])
    renderAt(page(), '/tournaments/NOPE')
    expect(await screen.findByText(/not found/i)).toBeInTheDocument()
  })
})

describe('PlayerPage tournament results', () => {
  it('shows season totals and results for the player', async () => {
    mockApi([
      ['/seasons', seasons],
      ['/players/1', { player_id: '1', display_name: 'Ada Birdie', is_active: true, country: 'Canada', primary_tour: 'PGA Tour', bio: null, seasons: [2025] }],
      ['/players/1/stats', []],
      [
        '/players/1/tournaments',
        {
          player_id: '1',
          display_name: 'Ada Birdie',
          season: 2025,
          totals: { starts: 21, cuts_made: 20, wins: 6, top_10s: 18, earnings_usd: 27_897_049.81, fedex_points: 7455.967 },
          results: [
            {
              tournament_id: 'R2025016',
              tournament_name: 'The Sentry',
              season: 2025,
              start_date: '2025-01-02',
              position_text: '1',
              position: 1,
              is_tied: false,
              status: 'finished',
              total_score: 257,
              to_par: -35,
              fedex_points: 700,
              earnings_usd: 3_600_000,
              field_size: 59,
            },
          ],
        },
      ],
    ])
    renderAt(
      <Routes>
        <Route path="/players/:id" element={<PlayerPage />} />
      </Routes>,
      '/players/1',
    )
    expect(await screen.findByRole('link', { name: 'The Sentry' })).toHaveAttribute('href', '/tournaments/R2025016')
    expect(screen.getByLabelText('Season totals')).toHaveTextContent('Wins6')
    expect(screen.getByLabelText('Season totals')).toHaveTextContent('$27.9M')
    expect(screen.getByText('Jan 2, 2025')).toBeInTheDocument()
  })
})
