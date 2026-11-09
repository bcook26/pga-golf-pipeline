import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { mockApi, renderAt } from '../test/helpers'
import { ComparePage } from './ComparePage'

const seasons = [{ season: 2025, players: 3, stats: 2, rows: 6 }]
const players = [
  { player_id: '1', display_name: 'Ada Birdie' },
  { player_id: '2', display_name: 'Ben Eagle' },
]
const v = (id: string, value: number | null, rank: number | null) => ({ player_id: id, stat_value: value, rank })
const comparison = {
  season: 2025,
  players,
  stats: [
    { stat_id: '02675', stat_name: 'SG: Total', categories: ['STROKES_GAINED'], values: [v('1', 1.5, 3), v('2', 2.5, 1)] },
    { stat_id: '101', stat_name: 'Driving Distance', categories: ['DRIVING'], values: [v('1', 300, 10), null] },
  ],
}
const history = {
  stat_id: '02675',
  stat_name: 'SG: Total',
  series: [
    { player_id: '1', display_name: 'Ada Birdie', points: [{ season: 2024, stat_value: 1, rank: 5 }, { season: 2025, stat_value: 1.5, rank: 3 }] },
    { player_id: '2', display_name: 'Ben Eagle', points: [{ season: 2025, stat_value: 2.5, rank: 1 }] },
  ],
}
const info = (id: string, name: string) => ({
  player_id: id, display_name: name, is_active: true, country: 'USA', primary_tour: 'PGA Tour', bio: null, seasons: [2025],
})

const routes: Array<[string, unknown]> = [
  ['/seasons', seasons],
  ['/players/1', info('1', 'Ada Birdie')],
  ['/players/2', info('2', 'Ben Eagle')],
  ['/compare/history', history],
  ['/compare?', comparison],
]

describe('ComparePage', () => {
  it('asks for players when none are selected and does not call the compare API', async () => {
    const calls = mockApi([['/seasons', seasons]])
    renderAt(<ComparePage />, '/compare')
    expect(screen.getByText('Add at least two players to compare.')).toBeInTheDocument()
    expect(calls.some((u) => u.includes('/compare'))).toBe(false)
  })

  it('asks for one more player when only one is selected', () => {
    mockApi([['/seasons', seasons], ['/players/1', info('1', 'Ada Birdie')]])
    renderAt(<ComparePage />, '/compare?p=0:1')
    expect(screen.getByText('Add one more player to start comparing.')).toBeInTheDocument()
  })

  it('shows the head-to-head table, highlights the best rank, and requests every selected player', async () => {
    const calls = mockApi(routes)
    renderAt(<ComparePage />, '/compare?p=0:1&p=1:2')

    // "Only stats all players have" hides Driving Distance (Ben has no value)
    const row = (await screen.findByRole('button', { name: 'SG: Total' })).closest('tr') as HTMLElement
    expect(screen.queryByRole('button', { name: 'Driving Distance' })).not.toBeInTheDocument()

    const cells = within(row).getAllByRole('cell')
    expect(cells[1]).not.toHaveClass('best') // Ada: rank 3
    expect(cells[2]).toHaveClass('best') // Ben: rank 1
    expect(cells[2]).toHaveTextContent('(best rank)')

    expect(calls.some((u) => u.includes('players=1') && u.includes('players=2') && u.includes('season=2025'))).toBe(true)
    expect(await screen.findByRole('heading', { name: 'SG: Total by season' })).toBeInTheDocument()
  })

  it('shows partial stats when the "all players" filter is turned off', async () => {
    mockApi(routes)
    renderAt(<ComparePage />, '/compare?p=0:1&p=1:2')
    await screen.findByRole('button', { name: 'SG: Total' })
    await userEvent.click(screen.getByLabelText('Only stats all players have'))
    const driving = (await screen.findByRole('button', { name: 'Driving Distance' })).closest('tr') as HTMLElement
    expect(within(driving).getAllByRole('cell')[2]).toHaveTextContent('–')
  })

  it('removing a player drops them from the URL state and keeps the others', async () => {
    mockApi(routes)
    renderAt(<ComparePage />, '/compare?p=0:1&p=1:2')
    await userEvent.click(await screen.findByRole('button', { name: 'Remove Ada Birdie' }))
    expect(await screen.findByText('Add one more player to start comparing.')).toBeInTheDocument()
    expect(screen.getByText('Ben Eagle')).toBeInTheDocument()
  })

  it('searches for and adds a player', async () => {
    mockApi([
      ...routes,
      ['/players?', { items: [{ player_id: '2', display_name: 'Ben Eagle', is_active: true, country: 'USA', primary_tour: 'PGA Tour' }], total: 1, limit: 8, offset: 0 }],
    ])
    renderAt(<ComparePage />, '/compare?p=0:1')
    await userEvent.type(screen.getByLabelText('Add a player'), 'ben')
    await userEvent.click(await screen.findByRole('button', { name: /Ben Eagle/ }))
    expect(await screen.findByRole('button', { name: 'SG: Total' })).toBeInTheDocument()
  })

  it('collapses long tables and expands on request', async () => {
    const many = Array.from({ length: 30 }, (_, i) => ({
      stat_id: `s${i}`, stat_name: `Stat ${String(i).padStart(2, '0')}`, categories: ['X'],
      values: [v('1', i, i + 1), v('2', i, i + 2)],
    }))
    mockApi([...routes.filter(([k]) => k !== '/compare?'), ['/compare?', { ...comparison, stats: many }]])
    renderAt(<ComparePage />, '/compare?p=0:1&p=1:2')
    await screen.findByRole('button', { name: 'Stat 00' })
    expect(screen.queryByRole('button', { name: 'Stat 25' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Show all 30 stats' }))
    expect(screen.getByRole('button', { name: 'Stat 25' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Show fewer stats' }))
    expect(screen.queryByRole('button', { name: 'Stat 25' })).not.toBeInTheDocument()
  })
})
