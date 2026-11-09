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
