import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api } from './client'

const HOUR = 60 * 60 * 1000

// Warehouse data changes at most daily, so cache generously.
export const useSeasons = () =>
  useQuery({ queryKey: ['seasons'], queryFn: ({ signal }) => api.seasons(signal), staleTime: HOUR })

export const useCategories = () =>
  useQuery({
    queryKey: ['categories'],
    queryFn: ({ signal }) => api.categories(signal),
    staleTime: HOUR,
  })

export const useStatCatalogue = (params: { search?: string; category?: string } = {}) =>
  useQuery({
    queryKey: ['stats', params],
    queryFn: ({ signal }) => api.stats(params, signal),
    staleTime: HOUR,
  })

export const usePlayers = (params: Parameters<typeof api.players>[0]) =>
  useQuery({
    queryKey: ['players', params],
    queryFn: ({ signal }) => api.players(params, signal),
    placeholderData: keepPreviousData, // no flicker while paging/typing
  })

export const usePlayer = (id: string) =>
  useQuery({ queryKey: ['player', id], queryFn: ({ signal }) => api.player(id, signal) })

export const usePlayerStats = (
  id: string,
  params: { season?: number; category?: string },
  enabled = true,
) =>
  useQuery({
    queryKey: ['player-stats', id, params],
    queryFn: ({ signal }) => api.playerStats(id, params, signal),
    placeholderData: keepPreviousData,
    enabled,
  })

export const useStatHistory = (id: string, statId: string | undefined) =>
  useQuery({
    queryKey: ['stat-history', id, statId],
    queryFn: ({ signal }) => api.statHistory(id, statId as string, signal),
    enabled: Boolean(statId),
  })

export const useLeaders = (statId: string, params: { season?: number; limit?: number }) =>
  useQuery({
    queryKey: ['leaders', statId, params],
    queryFn: ({ signal }) => api.leaders(statId, params, signal),
    enabled: Boolean(statId),
    placeholderData: keepPreviousData,
  })

export const useCompare = (
  players: string[],
  params: { season?: number; category?: string },
  enabled = true,
) =>
  useQuery({
    queryKey: ['compare', players, params],
    queryFn: ({ signal }) => api.compare(players, params, signal),
    enabled: enabled && players.length >= 2,
    placeholderData: keepPreviousData,
  })

export const useCompareHistory = (players: string[], statId: string | undefined) =>
  useQuery({
    queryKey: ['compare-history', players, statId],
    queryFn: ({ signal }) => api.compareHistory(players, statId as string, signal),
    enabled: players.length >= 2 && Boolean(statId),
  })

export const usePercentiles = (
  id: string | undefined,
  params: { season?: number; category?: string },
) =>
  useQuery({
    queryKey: ['percentiles', id, params],
    queryFn: ({ signal }) => api.percentiles(id as string, params, signal),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  })

export const useMovers = (
  statId: string,
  params: { season?: number; compare_to?: number; limit?: number },
) =>
  useQuery({
    queryKey: ['movers', statId, params],
    queryFn: ({ signal }) => api.movers(statId, params, signal),
    enabled: Boolean(statId),
    placeholderData: keepPreviousData,
  })

export const useScatter = (params: { x: string; y: string; season?: number }) =>
  useQuery({
    queryKey: ['scatter', params],
    queryFn: ({ signal }) => api.scatter(params, signal),
    enabled: Boolean(params.x && params.y && params.x !== params.y),
    placeholderData: keepPreviousData,
  })

// Operational data: refresh while the page is open.
export const usePipelineStatus = () =>
  useQuery({
    queryKey: ['pipeline-status'],
    queryFn: ({ signal }) => api.pipelineStatus(signal),
    refetchInterval: 30_000,
  })

export const useTournaments = (params: { season?: number; search?: string; category?: string }) =>
  useQuery({
    queryKey: ['tournaments', params],
    queryFn: ({ signal }) => api.tournaments(params, signal),
    placeholderData: keepPreviousData,
  })

export const useTournament = (id: string | undefined) =>
  useQuery({
    queryKey: ['tournament', id],
    queryFn: ({ signal }) => api.tournament(id as string, signal),
    enabled: Boolean(id),
  })

export const usePlayerTournaments = (
  id: string | undefined,
  params: { season?: number },
  enabled = true,
) =>
  useQuery({
    queryKey: ['player-tournaments', id, params],
    queryFn: ({ signal }) => api.playerTournaments(id as string, params, signal),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
  })
