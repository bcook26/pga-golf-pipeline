import type { components } from './schema'

type S = components['schemas']

// Types come straight from the API's OpenAPI schema (npm run gen:api).
export type PlayerSummary = S['PlayerSummary']
export type PlayerDetail = S['PlayerDetail']
export type PlayerStat = S['PlayerStat']
export type StatHistory = S['StatHistory']
export type StatDefinition = S['StatDefinition']
export type Leaderboard = S['Leaderboard']
export type SeasonInfo = S['SeasonInfo']
export type PlayersPage = S['Page_PlayerSummary_']
export type Comparison = S['Comparison']
export type CompareStat = S['CompareStat']
export type CompareValue = S['CompareValue']
export type ComparisonHistory = S['ComparisonHistory']

export const API_URL: string =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type Scalar = string | number | boolean | null | undefined
type Params = Record<string, Scalar | Scalar[]>

export function buildUrl(path: string, params: Params = {}): string {
  const url = new URL(path, API_URL)
  for (const [key, value] of Object.entries(params)) {
    // Arrays repeat the parameter: ?players=a&players=b
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item === undefined || item === null || item === '') continue
      url.searchParams.append(key, String(item))
    }
  }
  return url.toString()
}

async function get<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), { signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'Cannot reach the API. Is it running?')
  }
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

const V1 = '/api/v1'

export const api = {
  seasons: (signal?: AbortSignal) => get<SeasonInfo[]>(`${V1}/seasons`, undefined, signal),
  players: (
    params: {
      search?: string
      active?: boolean
      has_stats?: boolean
      season?: number
      limit?: number
      offset?: number
    },
    signal?: AbortSignal,
  ) => get<PlayersPage>(`${V1}/players`, params, signal),
  player: (id: string, signal?: AbortSignal) =>
    get<PlayerDetail>(`${V1}/players/${encodeURIComponent(id)}`, undefined, signal),
  playerStats: (
    id: string,
    params: { season?: number; category?: string },
    signal?: AbortSignal,
  ) => get<PlayerStat[]>(`${V1}/players/${encodeURIComponent(id)}/stats`, params, signal),
  statHistory: (id: string, statId: string, signal?: AbortSignal) =>
    get<StatHistory>(
      `${V1}/players/${encodeURIComponent(id)}/stats/${encodeURIComponent(statId)}/history`,
      undefined,
      signal,
    ),
  stats: (params: { search?: string; category?: string }, signal?: AbortSignal) =>
    get<StatDefinition[]>(`${V1}/stats`, params, signal),
  compare: (
    players: string[],
    params: { season?: number; category?: string },
    signal?: AbortSignal,
  ) => get<Comparison>(`${V1}/compare`, { players, ...params }, signal),
  compareHistory: (players: string[], statId: string, signal?: AbortSignal) =>
    get<ComparisonHistory>(`${V1}/compare/history`, { players, stat_id: statId }, signal),
  categories: (signal?: AbortSignal) => get<string[]>(`${V1}/stats/categories`, undefined, signal),
  leaders: (
    statId: string,
    params: { season?: number; limit?: number },
    signal?: AbortSignal,
  ) => get<Leaderboard>(`${V1}/stats/${encodeURIComponent(statId)}/leaders`, params, signal),
}
