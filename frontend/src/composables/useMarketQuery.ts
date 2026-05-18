import { useQuery, useMutation } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { marketApi } from '@/api/market'
import { queryClient } from '@/plugins/vue-query'

export function useWatchlist() {
  return useQuery({
    queryKey: ['market', 'watchlist'],
    queryFn: async () => ((await marketApi.getWatchlist()) as any).data,
  })
}

export function useKlines(params: MaybeRefOrGetter<{ symbol: string; market: string; timeframe: string; limit?: number }>) {
  return useQuery({
    queryKey: ['market', 'klines', params],
    queryFn: async () => ((await marketApi.getKlines(toValue(params))) as any).data,
    enabled: () => !!toValue(params).symbol,
  })
}

export function useTick(params: MaybeRefOrGetter<{ symbol: string; market: string }>) {
  return useQuery({
    queryKey: ['market', 'tick', params],
    queryFn: async () => ((await marketApi.getTick(toValue(params))) as any).data,
    enabled: () => !!toValue(params).symbol,
  })
}

export function useSymbolSearch(keyword: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: ['market', 'search', keyword],
    queryFn: async () => ((await marketApi.searchSymbols(toValue(keyword))) as any).data,
    enabled: () => !!toValue(keyword),
  })
}

export function useAddWatchlist() {
  return useMutation({
    mutationFn: (data: { symbol: string; market: string }) => marketApi.addWatchlist(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['market', 'watchlist'] })
    },
  })
}

export function useRemoveWatchlist() {
  return useMutation({
    mutationFn: (id: string) => marketApi.removeWatchlist(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['market', 'watchlist'] })
    },
  })
}
