import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { mockApi, renderAt } from '../test/helpers'
import { PipelinePage } from './PipelinePage'

const base = {
  generated_at: '2026-11-09T00:00:00Z',
  seasons: [{ season: 2026, rows: 88000, players: 180, stats: 400, last_success_at: '2026-11-08T00:00:00Z', age_seconds: 3600, last_run_status: 'success' }],
  quality: [{ run_id: 1, season: 2026, check_name: 'null_value_rate', status: 'warn', observed: 0.25, threshold: '0.2', detail: 'Null rate 25%', checked_at: '2026-11-08T00:00:00Z' }],
  runs: [{ run_id: 1, pipeline: 'stats', mode: 'incremental', season: 2026, status: 'success', rows_loaded: 88000, detail: null, started_at: '2026-11-08T00:00:00Z', finished_at: '2026-11-08T00:01:00Z', duration_seconds: 60 }],
}

describe('PipelinePage', () => {
  it('shows reasons, quality results and runs with text status', async () => {
    mockApi([['/pipeline/status', { ...base, overall: 'warn', reasons: ['null_value_rate warning in 2026'] }]])
    renderAt(<PipelinePage />)
    expect(await screen.findByText('Pipeline needs attention')).toBeInTheDocument()
    expect(screen.getByText('null_value_rate warning in 2026')).toBeInTheDocument()
    expect(screen.getAllByText('Warning').length).toBeGreaterThan(1)
    expect(screen.getAllByText('Success').length).toBeGreaterThan(0)
  })

  it('shows a healthy banner when there are no reasons', async () => {
    mockApi([['/pipeline/status', { ...base, overall: 'ok', reasons: [], quality: [] }]])
    renderAt(<PipelinePage />)
    expect(await screen.findByText('Pipeline healthy')).toBeInTheDocument()
    expect(screen.getByText(/no checks recorded/i)).toBeInTheDocument()
  })
})
